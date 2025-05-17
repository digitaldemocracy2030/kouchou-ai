import concurrent.futures
import json
import logging
import re

import pandas as pd
from pydantic import BaseModel, Field
from tqdm import tqdm

from services.category_classification import classify_args
from services.llm import request_to_chat_ai
from services.parse_json_list import parse_extraction_response
from utils import update_progress

COMMA_AND_SPACE_AND_RIGHT_BRACKET = re.compile(r",\s*(\])")


class ExtractionResponse(BaseModel):
    extractedOpinionList: list[str] = Field(..., description="抽出した意見のリスト")


def _validate_property_columns(property_columns: list[str], comments: pd.DataFrame) -> None:
    if not all(property in comments.columns for property in property_columns):
        raise ValueError(f"Properties {property_columns} not found in comments. Columns are {comments.columns}")


def extraction(config):
    dataset = config["output_dir"]
    path = f"outputs/{dataset}/args.csv"
    model = config["extraction"]["model"]
    prompt = config["extraction"]["prompt"]
    workers = config["extraction"]["workers"]
    limit = config["extraction"]["limit"]
    property_columns = config["extraction"]["properties"]

    if "provider" not in config:
        raise RuntimeError("provider is not set")
    provider = config["provider"]

    # カラム名だけを読み込み、必要なカラムが含まれているか確認する
    comments = pd.read_csv(f"inputs/{config['input']}.csv", nrows=0)
    _validate_property_columns(property_columns, comments)
    # エラーが出なかった場合、すべての行を読み込む
    comments = pd.read_csv(
        f"inputs/{config['input']}.csv", usecols=["comment-id", "comment-body"] + config["extraction"]["properties"]
    )
    comment_ids = (comments["comment-id"].values)[:limit]
    comments.set_index("comment-id", inplace=True)
    results = pd.DataFrame()
    update_progress(config, total=len(comment_ids))

    argument_map = {}
    relation_rows = []

    for i in tqdm(range(0, len(comment_ids), workers)):
        batch = comment_ids[i : i + workers]
        batch_inputs = [comments.loc[id]["comment-body"] for id in batch]
        batch_results = extract_batch(batch_inputs, prompt, model, workers, provider, config.get("local_llm_address"))

        for comment_id, extracted_args in zip(batch, batch_results, strict=False):
            for j, arg in enumerate(extracted_args):
                if arg not in argument_map:
                    # argumentテーブルに追加
                    arg_id = f"A{comment_id}_{j}"
                    argument_map[arg] = {
                        "arg-id": arg_id,
                        "argument": arg,
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
    results = pd.DataFrame(argument_map.values())
    relation_df = pd.DataFrame(relation_rows)

    if results.empty:
        raise RuntimeError("result is empty, maybe bad prompt")

    classification_categories = config["extraction"]["categories"]
    if classification_categories:
        results = classify_args(results, config, workers)

    results.to_csv(path, index=False)
    # comment-idとarg-idの関係を保存
    relation_df.to_csv(f"outputs/{dataset}/relations.csv", index=False)


logging.basicConfig(level=logging.ERROR)


def extract_batch(batch, prompt, model, workers, provider="openai", local_llm_address=None):
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures_with_index = [
            (i, executor.submit(extract_arguments, input, prompt, model, provider, local_llm_address))
            for i, input in enumerate(batch)
        ]

        done, not_done = concurrent.futures.wait([f for _, f in futures_with_index], timeout=30)
        results = [[] for _ in range(len(batch))]

        for _, future in futures_with_index:
            if future in not_done and not future.cancelled():
                future.cancel()

        for i, future in futures_with_index:
            if future in done:
                try:
                    result = future.result()
                    results[i] = result
                except Exception as e:
                    logging.error(f"Task {future} failed with error: {e}")
                    results[i] = []
        return results


def extract_arguments(input, prompt, model, provider="openai", local_llm_address=None):
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": input},
    ]
    try:
        response = request_to_chat_ai(
            messages=messages,
            model=model,
            is_json=False,
            json_schema=ExtractionResponse,
            provider=provider,
            local_llm_address=local_llm_address,
        )
        items = parse_extraction_response(response)
        items = filter(None, items)  # omit empty strings
        return items
    except json.decoder.JSONDecodeError as e:
        print("JSON error:", e)
        print("Input was:", input)
        print("Response was:", response)
        print("Silently giving up on trying to generate valid list.")
        return []
