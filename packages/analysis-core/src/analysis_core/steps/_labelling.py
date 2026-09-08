"""Shared failure handling for concurrent cluster labelling."""

import json
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

from pydantic import ValidationError

_usage_lock = Lock()


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


def run_labelling_batch(process, cluster_ids, workers, stage):
    results = []
    failures = {}
    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [(cluster_id, executor.submit(process, cluster_id)) for cluster_id in cluster_ids]
        for cluster_id, future in futures:
            try:
                results.append(future.result())
            except Exception as exc:
                kind = type(exc).__name__
                if isinstance(exc, (InvalidLabelResponse, json.JSONDecodeError, ValidationError)):
                    kind = "invalid_response"
                elif isinstance(exc, TimeoutError) or "timeout" in kind.lower():
                    kind = "timeout"
                failures[str(cluster_id)] = kind
    if failures:
        raise LabellingBatchError(stage, failures)
    return results
