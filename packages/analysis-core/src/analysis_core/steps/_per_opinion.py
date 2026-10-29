"""意見 1 件ごとに LLM を呼ぶ任意ステップ（意見分類・賛否スコア）で共有する実行ループ。

``args.csv`` の全件を ``workers`` 本のプールで回し、結果を入力順に返す。1 件でも失敗したら
新しい要求は出さず、実行中の要求の完了を待ってから ``PerOpinionBatchError`` を送出する。
失敗の内訳（arg-id → 分類名）には意見本文や API キーを含めない。
"""

import logging
from collections.abc import Callable
from typing import Any, TypeVar

from analysis_core.services.error_summary import summarize_exception
from analysis_core.steps._labelling import record_usage
from analysis_core.steps._pool import iter_pool_completed

T = TypeVar("T")


class PerOpinionBatchError(RuntimeError):
    """Some opinions could not be processed; partial results are not written."""

    #: 失敗メッセージに出す処理名（サブクラスで上書きする）
    task_name = "意見ごとの処理"

    def __init__(self, failures: dict[str, str]):
        self.failures = failures
        super().__init__(
            f"{self.task_name}に失敗した意見が{len(failures)}件あります。分析を中断しました。 (arg-id / error: {failures})"
        )


def run_per_opinion(
    arg_ids: list[str],
    texts: list[str],
    call: Callable[[str], tuple[T, int, int, int]],
    workers: int,
    *,
    config: dict | None,
    user_api_key: str | None,
    invalid_response_type: type[Exception],
    error_type: type[PerOpinionBatchError],
    task_name: str,
    on_progress: Callable[[int], None] | None = None,
) -> list[T]:
    """``texts`` の各要素に ``call`` を適用し、結果を入力順に返す。

    ``call`` は ``(result, token_input, token_output, token_total)`` を返す。
    ``invalid_response_type`` の例外は ``invalid_response``、それ以外は例外の型名として失敗に記録する。
    進捗（on_progress）は workers 件の完了ごとにまとめて呼ぶ。
    """
    results: list[Any] = [None for _ in texts]
    failures: dict[str, str] = {}
    flush_every = max(1, int(workers))
    completed = 0
    # 1 リクエストの上限は SDK に渡す timeout_seconds が担う。プール側で同じ値の
    # 待機上限を重ねると、遅れて成功した応答まで TimeoutError として捨ててしまう。
    for index, future in iter_pool_completed(call, texts, workers, stop=lambda: bool(failures)):
        arg_id = arg_ids[index]
        try:
            result, token_input, token_output, token_total = future.result()
        except invalid_response_type as exc:
            failures[arg_id] = "invalid_response"
            logging.error("%sに失敗しました。意見 %s: %s", task_name, arg_id, summarize_exception(exc, (user_api_key,)))
        except Exception as exc:
            # status には分類名（型名）だけを残し、理由は秘密情報を伏せて通常ログに出す
            failures[arg_id] = type(exc).__name__
            logging.error("%sに失敗しました。意見 %s: %s", task_name, arg_id, summarize_exception(exc, (user_api_key,)))
        else:
            record_usage(config, token_input, token_output, token_total)
            results[index] = result
        completed += 1
        if completed >= flush_every:
            if on_progress is not None:
                on_progress(completed)
            completed = 0
    if completed and on_progress is not None:
        on_progress(completed)

    if failures:
        raise error_type(failures)
    return results
