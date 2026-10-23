import json
import logging
import os
import re
from pathlib import Path

import polars as pl
from pydantic import BaseModel, Field
from tqdm import tqdm

from analysis_core.core import update_progress
from analysis_core.core.utils import read_input_csv
from analysis_core.services.llm import request_to_chat_ai
from analysis_core.services.parse_json_list import parse_extraction_response
from analysis_core.services.timeouts import DEFAULT_REQUEST_TIMEOUT_SECONDS, resolve_timeout
from analysis_core.steps._pool import iter_pool_completed

COMMA_AND_SPACE_AND_RIGHT_BRACKET = re.compile(r",\s*(\])")
EXTRACTION_WAIT_TIMEOUT_SECONDS = DEFAULT_REQUEST_TIMEOUT_SECONDS


class ExtractionResponse(BaseModel):
    extractedOpinionList: list[str] = Field(..., description="抽出した意見のリスト")


class ExtractionBatchError(RuntimeError):
    """A batch contains failed responses and must not reach downstream analysis."""

    def __init__(self, failures, comment_ids=None):
        self.failures = failures
        identifiers = {comment_ids[i] if comment_ids is not None else i: reason for i, reason in failures.items()}
        super().__init__(
            f"意見抽出に失敗した回答が{len(failures)}件あります。分析を中断しました。"
            f" ({'回答ID' if comment_ids is not None else 'batch index'} / error: {identifiers})"
        )


def _validate_property_columns(property_columns: list[str], comments: pl.DataFrame) -> None:
    """Raise ValueError if any required property column is missing from the DataFrame."""
    if not all(property in comments.columns for property in property_columns):
        raise ValueError(f"Properties {property_columns} not found in comments. Columns are {comments.columns}")


def _filter_empty_comments(comments: pl.DataFrame) -> pl.DataFrame:
    """Filter out rows where comment-body is null or contains only whitespace.

    Logs the number of filtered rows and raises RuntimeError if all comments are empty.
    """
    original_count = len(comments)
    normalized_comment_body = pl.col("comment-body").cast(pl.String, strict=False).fill_null("")
    filtered = comments.filter(
        normalized_comment_body.str.strip_chars() != ""
    )
    filtered_count = original_count - len(filtered)
    if filtered_count > 0:
        logging.info("Filtered out %d empty/whitespace-only comments out of %d", filtered_count, original_count)
    if len(filtered) == 0:
        raise RuntimeError("All comments are empty or whitespace-only after filtering")
    return filtered


def filter_empty_comments(comments: pl.DataFrame) -> pl.DataFrame:
    """Public wrapper for filtering empty/whitespace-only comments before LLM processing."""
    return _filter_empty_comments(comments)


def extraction(config):
    """Extract arguments from comments using LLM, skipping empty/whitespace-only entries."""
    dataset = config["output_dir"]
    output_base_dir = config.get("_output_base_dir", "outputs")
    input_base_dir = config.get("_input_base_dir", "inputs")
    path = f"{output_base_dir}/{dataset}/args.csv"
    model = config["extraction"]["model"]
    prompt = config["extraction"]["prompt"]
    workers = config["extraction"]["workers"]
    limit = config["extraction"]["limit"]
    property_columns = config["extraction"]["properties"]
    timeout_seconds = resolve_timeout(config["extraction"].get("timeout_seconds"))
    user_api_key = config.get("user_api_key") or os.getenv("USER_API_KEY")

    if "provider" not in config:
        raise RuntimeError("provider is not set")
    provider = config["provider"]

    # カラム名だけを読み込み、必要なカラムが含まれているか確認する
    input_path = f"{input_base_dir}/{config['input']}.csv"
    comments = read_input_csv(input_path, n_rows=0)
    _validate_property_columns(property_columns, comments)
    # エラーが出なかった場合、すべての行を読み込む
    comments = read_input_csv(input_path, columns=["comment-id", "comment-body"] + config["extraction"]["properties"])

    # 空文字列・空白のみのコメントを除外する (#583)
    comments = _filter_empty_comments(comments)

    comment_ids = comments["comment-id"].to_list()[:limit]
    comments_lookup = {row["comment-id"]: row for row in comments.iter_rows(named=True)}
    update_progress(config, total=len(comment_ids))

    # Keep original comments outside the published outputs tree.
    diagnostics_dir = Path(output_base_dir).resolve().parent / "diagnostics"
    diagnostics_dir.mkdir(parents=True, exist_ok=True)
    diagnostics_path = diagnostics_dir / f"{Path(dataset).name}-extraction.jsonl"
    fd = os.open(diagnostics_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    os.close(fd)
    logging.info("抽出診断（原文を含む非公開ファイル）: %s", diagnostics_path)

    argument_map = {}
    relation_rows = []

    # 全回答を 1 つのプール（workers 本）で回す。workers 件ずつのバッチの完了を待つと、
    # バッチ内で最も遅い 1 件の応答が終わるまで他の worker が遊ぶ。
    batch_inputs = [comments_lookup[id]["comment-body"] for id in comment_ids]
    with tqdm(total=len(comment_ids)) as progress_bar:

        def on_progress(count):
            progress_bar.update(count)
            update_progress(config, incr=count)

        all_results = extract_batch(
            batch_inputs,
            prompt,
            model,
            workers,
            provider,
            config.get("local_llm_address"),
            config,
            timeout_seconds,
            user_api_key,
            comment_ids=comment_ids,
            diagnostics_path=diagnostics_path,
            on_progress=on_progress,
        )

    # 結果は入力順に並んでいるので、args.csv / relations.csv の行順は回答の順のまま
    for comment_id, extracted_args in zip(comment_ids, all_results, strict=True):
        for j, arg in enumerate(extracted_args):
            # 同じ文面でも回答ごとに別の意見として扱う。回答をまたいでまとめると、
            # 集計で意見1件に回答1件分の属性・URLしか残らず、他の回答者の帰属が消える。
            key = (comment_id, arg)
            if key not in argument_map:
                # argumentテーブルに追加
                arg_id = f"A{comment_id}_{j}"
                argument = arg
                argument_map[key] = {
                    "arg-id": arg_id,
                    "argument": argument,
                }
            else:
                arg_id = argument_map[key]["arg-id"]

            # relationテーブルにcommentとargの関係を追加
            relation_row = {
                "arg-id": arg_id,
                "comment-id": comment_id,
            }
            relation_rows.append(relation_row)

    # DataFrame化
    results = pl.DataFrame(list(argument_map.values()))
    relation_df = pl.DataFrame(relation_rows)

    if len(results) == 0:
        raise RuntimeError("result is empty, maybe bad prompt")

    results.write_csv(path)
    # comment-idとarg-idの関係を保存
    relation_df.write_csv(f"{output_base_dir}/{dataset}/relations.csv")


def extract_batch(
    batch,
    prompt,
    model,
    workers,
    provider="openai",
    local_llm_address=None,
    config=None,
    timeout_seconds=EXTRACTION_WAIT_TIMEOUT_SECONDS,
    user_api_key=None,
    comment_ids=None,
    diagnostics_path=None,
    on_progress=None,
):
    """Run argument extraction concurrently with a pool of ``workers`` threads.

    空いた worker にはすぐ次の回答を渡し、結果は入力順に返す。
    失敗を検知したら新しい要求は出さず、実行中の要求の完了を待ってから
    ExtractionBatchError を送出する（完了した要求のトークンは集計し、診断ファイルにも書く）。
    トークン集計・進捗（on_progress）・診断ファイルへの追記は、workers 件の完了ごとに
    呼び出し元のスレッドでまとめて行う。
    """
    results = [[] for _ in range(len(batch))]
    failures = {}
    flush_every = max(1, int(workers))
    pending = {"count": 0, "input": 0, "output": 0, "total": 0, "diagnostics": []}

    def flush():
        if pending["count"] == 0:
            return
        if config is not None:
            config["total_token_usage"] = config.get("total_token_usage", 0) + pending["total"]
            config["token_usage_input"] = config.get("token_usage_input", 0) + pending["input"]
            config["token_usage_output"] = config.get("token_usage_output", 0) + pending["output"]
            print(
                f"Extraction batch: input={pending['input']}, output={pending['output']}, total={pending['total']} tokens"
            )
        if diagnostics_path is not None and pending["diagnostics"]:
            with open(diagnostics_path, "a", encoding="utf-8") as diagnostic_file:
                for index in sorted(pending["diagnostics"]):
                    record = {
                        "comment_id": comment_ids[index] if comment_ids is not None else index,
                        "comment": batch[index],
                        "status": "error" if index in failures else "empty",
                        "error_type": failures.get(index),
                    }
                    diagnostic_file.write(json.dumps(record, ensure_ascii=False) + "\n")
        if on_progress is not None:
            on_progress(pending["count"])
        pending.update(count=0, input=0, output=0, total=0, diagnostics=[])

    def run(input):
        return extract_arguments(input, prompt, model, provider, local_llm_address, timeout_seconds, user_api_key)

    # 1 リクエストの上限は各プロバイダの SDK に渡す timeout_seconds が担う。
    # プール側で同じ値の待機上限を重ねると、Flex (最大 900 秒) や SDK 内部の再試行で
    # timeout_seconds を超えて成功した応答まで TimeoutError として捨ててしまう。
    for i, future in iter_pool_completed(run, batch, workers, stop=lambda: bool(failures)):
        try:
            result = future.result()
            if isinstance(result, tuple) and len(result) == 4:
                items, token_input, token_output, token_total = result
                results[i] = items
                pending["input"] += token_input
                pending["output"] += token_output
                pending["total"] += token_total
            else:
                results[i] = result
        except Exception as e:
            failures[i] = type(e).__name__
        if i in failures or not results[i]:
            pending["diagnostics"].append(i)
        pending["count"] += 1
        if pending["count"] >= flush_every:
            flush()
    flush()

    if failures:
        raise ExtractionBatchError(failures, comment_ids)
    return results


def extract_arguments(
    input,
    prompt,
    model,
    provider="openai",
    local_llm_address=None,
    timeout_seconds=EXTRACTION_WAIT_TIMEOUT_SECONDS,
    user_api_key=None,
):
    """Send a single comment to the LLM and return extracted arguments."""
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": input},
    ]
    response, token_input, token_output, token_total = request_to_chat_ai(
        messages=messages,
        model=model,
        is_json=False,
        json_schema=ExtractionResponse,
        provider=provider,
        local_llm_address=local_llm_address,
        user_api_key=user_api_key or os.getenv("USER_API_KEY"),
        timeout_seconds=timeout_seconds,
    )
    items = parse_extraction_response(response)
    items = list(filter(None, items))  # omit empty strings
    return items, token_input, token_output, token_total
