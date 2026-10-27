"""Shared failure handling for concurrent cluster labelling."""

import json
import logging
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

import openai
from pydantic import ValidationError

from analysis_core.services.error_summary import summarize_exception

_usage_lock = Lock()
# 形式不正・途中切れの応答を受けたときに、同じクラスタを送り直す回数の上限（初回を含む）。
# ラベル生成は送るたびに意見を選び直すので、送り直すと入力も変わる。
LABELLING_MALFORMED_RESPONSE_MAX_ATTEMPTS = 3


class InvalidLabelResponse(ValueError):
    pass


class LabellingBatchError(RuntimeError):
    def __init__(self, stage, failures):
        self.failures = failures
        details = ", ".join(f"{cluster_id} ({kind})" for cluster_id, kind in failures.items())
        super().__init__(
            f"{stage}: ラベル生成に{len(failures)}件失敗しました。クラスタ: {details}。"
            "処理を中止しました。トークン使用量・費用の集計は不完全です。"
        )


def parse_label(response):
    try:
        data = json.loads(response) if isinstance(response, str) else response
        if not isinstance(data, dict) or any(
            not isinstance(data.get(key), str) or not data[key].strip() for key in ("label", "description")
        ):
            raise ValueError
        return data
    except (ValueError, TypeError) as exc:
        raise InvalidLabelResponse("ラベル応答の形式が不正です") from exc


def record_usage(config, token_input, token_output, token_total):
    if config is not None:
        # Workers share config; read-modify-write must be atomic.
        with _usage_lock:
            for key, count in (
                ("total_token_usage", token_total),
                ("token_usage_input", token_input),
                ("token_usage_output", token_output),
            ):
                config[key] = config.get(key, 0) + count


def _is_malformed_response(exc):
    return isinstance(
        exc, (InvalidLabelResponse, json.JSONDecodeError, ValidationError, openai.LengthFinishReasonError)
    )


def _process_with_retry(process, cluster_id, stage):
    """形式不正・途中切れの応答なら、このクラスタだけを送り直す。

    gpt-4o は temperature=0 でも、まれに同じ語句を出力の上限（16384 トークン）まで繰り返し、
    LengthFinishReasonError になる。1 クラスタのこの不調でパイプライン全体が止まっていた。
    API エラーは SDK とプロバイダ側の再試行に任せ、ここでは送り直さない。
    """
    for attempt in range(1, LABELLING_MALFORMED_RESPONSE_MAX_ATTEMPTS + 1):
        try:
            return process(cluster_id)
        except Exception as exc:
            if not _is_malformed_response(exc) or attempt >= LABELLING_MALFORMED_RESPONSE_MAX_ATTEMPTS:
                raise
            # 応答本文はログに出さない（例外の種類だけを残す）
            logging.warning(
                "%s: クラスタ %s のラベル応答を解釈できなかったため、送り直します（%s、%d/%d 回目）",
                stage,
                cluster_id,
                type(exc).__name__,
                attempt,
                LABELLING_MALFORMED_RESPONSE_MAX_ATTEMPTS,
            )
    raise AssertionError("unreachable")  # pragma: no cover


def run_labelling_batch(process, cluster_ids, workers, stage, secrets: Iterable[str | None] = ()):
    """クラスタごとのラベル生成を並列に行い、失敗があればまとめて LabellingBatchError にする。

    形式不正・途中切れの応答は、そのクラスタだけを LABELLING_MALFORMED_RESPONSE_MAX_ATTEMPTS 回まで送り直す。
    status に入る例外メッセージは分類名だけにし、理由は秘密情報を伏せたうえで通常ログに出す。
    """
    secrets = tuple(secrets)
    results = []
    failures = {}
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [
            (cluster_id, executor.submit(_process_with_retry, process, cluster_id, stage)) for cluster_id in cluster_ids
        ]
        for cluster_id, future in futures:
            try:
                results.append(future.result())
            except Exception as exc:
                kind = type(exc).__name__
                if _is_malformed_response(exc):
                    kind = "invalid_response"
                elif isinstance(exc, TimeoutError) or "timeout" in kind.lower():
                    kind = "timeout"
                failures[str(cluster_id)] = kind
                logging.error(
                    "%s: ラベル生成に失敗しました。クラスタ %s: %s",
                    stage,
                    cluster_id,
                    summarize_exception(exc, secrets),
                )
    if failures:
        raise LabellingBatchError(stage, failures)
    return results
