import concurrent.futures
import json
import logging
import os
import re
from pathlib import Path

import openai
import polars as pl
from pydantic import BaseModel, Field, ValidationError
from tqdm import tqdm

from analysis_core.core import update_progress
from analysis_core.core.utils import read_input_csv
from analysis_core.services.llm import request_to_chat_ai
from analysis_core.services.parse_json_list import parse_extraction_response
from analysis_core.services.timeouts import DEFAULT_REQUEST_TIMEOUT_SECONDS, resolve_timeout

COMMA_AND_SPACE_AND_RIGHT_BRACKET = re.compile(r",\s*(\])")
EXTRACTION_WAIT_TIMEOUT_SECONDS = DEFAULT_REQUEST_TIMEOUT_SECONDS
# 形式不正・途中切れの応答を受けたときに、同じ回答を送り直す回数の上限（初回を含む）。
EXTRACTION_MALFORMED_RESPONSE_MAX_ATTEMPTS = 3


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

    for i in tqdm(range(0, len(comment_ids), workers)):
        batch = comment_ids[i : i + workers]
        batch_inputs = [comments_lookup[id]["comment-body"] for id in batch]
        batch_results = extract_batch(
            batch_inputs,
            prompt,
            model,
            workers,
            provider,
            config.get("local_llm_address"),
            config,
            timeout_seconds,
            user_api_key,
            comment_ids=batch,
            diagnostics_path=diagnostics_path,
        )

        for comment_id, extracted_args in zip(batch, batch_results, strict=False):
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

        update_progress(config, incr=len(batch))

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
):
    """Run argument extraction concurrently for a batch of comment texts."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures_with_index = [
            (
                i,
                executor.submit(
                    extract_arguments,
                    input,
                    prompt,
                    model,
                    provider,
                    local_llm_address,
                    timeout_seconds,
                    user_api_key,
                ),
            )
            for i, input in enumerate(batch)
        ]

        # 1 リクエストの上限は各プロバイダの SDK に渡す timeout_seconds が担う。
        # バッチ側で同じ値の待機上限を重ねると、Flex (最大 900 秒) や SDK 内部の再試行で
        # timeout_seconds を超えて成功した応答まで TimeoutError として捨ててしまう。
        # 実行中の future は cancel できず executor の終了時に待つことになるため、
        # バッチ側の待機上限は所要時間も短くしない。
        concurrent.futures.wait([f for _, f in futures_with_index])
        results = [[] for _ in range(len(batch))]
        failures = {}
        total_token_input = 0
        total_token_output = 0
        total_token_usage = 0

        for i, future in futures_with_index:
            try:
                result = future.result()
                if isinstance(result, tuple) and len(result) == 4:
                    items, token_input, token_output, token_total = result
                    results[i] = items
                    total_token_input += token_input
                    total_token_output += token_output
                    total_token_usage += token_total
                else:
                    results[i] = result
            except Exception as e:
                failures[i] = type(e).__name__

        if config is not None:
            config["total_token_usage"] = config.get("total_token_usage", 0) + total_token_usage
            config["token_usage_input"] = config.get("token_usage_input", 0) + total_token_input
            config["token_usage_output"] = config.get("token_usage_output", 0) + total_token_output
            print(
                f"Extraction batch: input={total_token_input}, output={total_token_output}, total={total_token_usage} tokens"
            )

        if diagnostics_path is not None:
            with open(diagnostics_path, "a", encoding="utf-8") as diagnostic_file:
                for index, items in enumerate(results):
                    if index not in failures and items:
                        continue
                    record = {
                        "comment_id": comment_ids[index] if comment_ids is not None else index,
                        "comment": batch[index],
                        "status": "error" if index in failures else "empty",
                        "error_type": failures.get(index),
                    }
                    diagnostic_file.write(json.dumps(record, ensure_ascii=False) + "\n")
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
    """Send a single comment to the LLM and return extracted arguments.

    応答が形式不正・途中切れのとき（JSON の不正・スキーマ違反・finish_reason=length）は、
    この回答だけを EXTRACTION_MALFORMED_RESPONSE_MAX_ATTEMPTS 回まで送り直す。200 で返った
    応答の中身の不正は SDK も再試行しないため、1 件の不調で抽出全体が中断していた。
    API エラーと、拒否・コンテンツフィルタは送り直しても変わらないか SDK が扱うので、そのまま送出する。
    拒否・コンテンツフィルタは経路によって返り方が違う。OpenAI・Azure・OpenRouter の構造化出力
    （parse）経路では内容なし（None）か SDK の例外で返り、OpenRouter の JSON fallback 経路と
    ローカル LLM 経路では本文（「I'm sorry...」など）や空文字列で返る。後者は JSON の括弧を
    含まない本文として見分ける（_looks_like_json_attempt）。送り直した分のトークンも課金されて
    いるので合計に含める。
    """
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": input},
    ]
    total_input = total_output = total_tokens = 0
    for attempt in range(1, EXTRACTION_MALFORMED_RESPONSE_MAX_ATTEMPTS + 1):
        try:
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
        except (ValidationError, openai.LengthFinishReasonError) as error:
            # SDK の構造化出力の parse が、途中で切れた・スキーマに合わない応答を弾いた
            token_input, token_output, token_total = _token_usage_of_failed_completion(error)
            total_input += token_input
            total_output += token_output
            total_tokens += token_total
            if attempt >= EXTRACTION_MALFORMED_RESPONSE_MAX_ATTEMPTS:
                raise
            _log_malformed_retry(error, attempt)
            continue

        total_input += token_input
        total_output += token_output
        total_tokens += token_total
        try:
            items = parse_extraction_response(response)
        except ValueError as error:
            # 内容が無い応答や、JSON を書こうとしていない本文（拒否・コンテンツフィルタの空応答）は
            # 送り直しても変わらないので、再試行しない
            if not _looks_like_json_attempt(response) or attempt >= EXTRACTION_MALFORMED_RESPONSE_MAX_ATTEMPTS:
                raise
            _log_malformed_retry(error, attempt)
            continue
        items = list(filter(None, items))  # omit empty strings
        return items, total_input, total_output, total_tokens

    raise AssertionError("unreachable")  # pragma: no cover


def _looks_like_json_attempt(response: str | dict | None) -> bool:
    """応答が JSON を書こうとした形か（壊れていても送り直す価値があるか）。

    JSON fallback 経路やローカル LLM 経路の拒否・コンテンツフィルタは、括弧を含まない本文や空文字列で返る。
    これらは決定的に繰り返されるので、形式不正（途中切れ・スキーマ違反）と区別して送り直さない。
    """
    if response is None:
        return False
    if not isinstance(response, str):
        return True
    return "{" in response or "[" in response


def _token_usage_of_failed_completion(error: Exception) -> tuple[int, int, int]:
    """finish_reason=length で弾かれた応答の usage（取れない場合は 0）。"""
    usage = getattr(getattr(error, "completion", None), "usage", None)
    if usage is None:
        return 0, 0, 0
    return usage.prompt_tokens or 0, usage.completion_tokens or 0, usage.total_tokens or 0


def _log_malformed_retry(error: Exception, attempt: int) -> None:
    # 応答本文・原文は公開ログに出さない（例外の種類だけを残す）
    logging.warning(
        "意見抽出の応答を解釈できなかったため、同じ回答を送り直します（%s、%d/%d 回目）",
        type(error).__name__,
        attempt,
        EXTRACTION_MALFORMED_RESPONSE_MAX_ATTEMPTS,
    )
