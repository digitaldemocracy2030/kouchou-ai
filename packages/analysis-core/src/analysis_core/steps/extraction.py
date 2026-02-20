import concurrent.futures
import json
import logging
import os
import re

import polars as pl
from pydantic import BaseModel, Field
from tqdm import tqdm

from analysis_core.core import update_progress
from analysis_core.services.llm import request_to_chat_ai
from analysis_core.services.parse_json_list import parse_extraction_response

COMMA_AND_SPACE_AND_RIGHT_BRACKET = re.compile(r",\s*(\])")


class ExtractionResponse(BaseModel):
    extractedOpinionList: list[str] = Field(..., description="抽出した意見のリスト")


def _validate_property_columns(property_columns: list[str], comments: pl.DataFrame) -> None:
    """Raise ValueError if any required property column is missing from the DataFrame."""
    if not all(property in comments.columns for property in property_columns):
        raise ValueError(f"Properties {property_columns} not found in comments. Columns are {comments.columns}")


def _filter_empty_comments(comments: pl.DataFrame) -> pl.DataFrame:
    """Filter out rows where comment-body is null or contains only whitespace.

    Logs the number of filtered rows and raises RuntimeError if all comments are empty.
    """
    original_count = len(comments)
    filtered = comments.filter(
        pl.col("comment-body").is_not_null() & (pl.col("comment-body").str.strip_chars() != "")
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

    if "provider" not in config:
        raise RuntimeError("provider is not set")
    provider = config["provider"]

    # カラム名だけを読み込み、必要なカラムが含まれているか確認する
    input_path = f"{input_base_dir}/{config['input']}.csv"
    comments = pl.read_csv(input_path, n_rows=0)
    _validate_property_columns(property_columns, comments)
    # エラーが出なかった場合、すべての行を読み込む
    comments = pl.read_csv(input_path, columns=["comment-id", "comment-body"] + config["extraction"]["properties"])

    # 空文字列・空白のみのコメントを除外する (#583)
    comments = _filter_empty_comments(comments)

    comment_ids = comments["comment-id"].to_list()[:limit]
    comments_lookup = {row["comment-id"]: row for row in comments.iter_rows(named=True)}
    update_progress(config, total=len(comment_ids))

    argument_map = {}
    relation_rows = []

    for i in tqdm(range(0, len(comment_ids), workers)):
        batch = comment_ids[i : i + workers]
        batch_inputs = [comments_lookup[id]["comment-body"] for id in batch]
        batch_results = extract_batch(
            batch_inputs, prompt, model, workers, provider, config.get("local_llm_address"), config
        )

        for comment_id, extracted_args in zip(batch, batch_results, strict=False):
            for j, arg in enumerate(extracted_args):
                if arg not in argument_map:
                    # argumentテーブルに追加
                    arg_id = f"A{comment_id}_{j}"
                    argument = arg
                    argument_map[arg] = {
                        "arg-id": arg_id,
                        "argument": argument,
                    }
                else:
                    arg_id = argument_map[arg]["arg-id"]

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


def extract_batch(batch, prompt, model, workers, provider="openai", local_llm_address=None, config=None):
    """Run argument extraction concurrently for a batch of comment texts."""
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures_with_index = [
            (i, executor.submit(extract_arguments, input, prompt, model, provider, local_llm_address))
            for i, input in enumerate(batch)
        ]

        done, not_done = concurrent.futures.wait([f for _, f in futures_with_index], timeout=30)
        results = [[] for _ in range(len(batch))]
        total_token_input = 0
        total_token_output = 0
        total_token_usage = 0

        for _, future in futures_with_index:
            if future in not_done and not future.cancelled():
                future.cancel()

        for i, future in futures_with_index:
            if future in done:
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
                    logging.error(f"Task {future} failed with error: {e}")
                    results[i] = []

        if config is not None:
            config["total_token_usage"] = config.get("total_token_usage", 0) + total_token_usage
            config["token_usage_input"] = config.get("token_usage_input", 0) + total_token_input
            config["token_usage_output"] = config.get("token_usage_output", 0) + total_token_output
            print(
                f"Extraction batch: input={total_token_input}, output={total_token_output}, total={total_token_usage} tokens"
            )

        return results


def extract_arguments(input, prompt, model, provider="openai", local_llm_address=None):
    """Send a single comment to the LLM and return extracted arguments."""
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": input},
    ]
    try:
        response, token_input, token_output, token_total = request_to_chat_ai(
            messages=messages,
            model=model,
            is_json=False,
            json_schema=ExtractionResponse,
            provider=provider,
            local_llm_address=local_llm_address,
            user_api_key=os.getenv("USER_API_KEY"),
        )
        items = parse_extraction_response(response)
        items = list(filter(None, items))  # omit empty strings
        return items, token_input, token_output, token_total
    except json.decoder.JSONDecodeError as e:
        print("JSON error:", e)
        print("Input was:", input)
        print("Response was:", response)
        print("Silently giving up on trying to generate valid list.")
        return []
