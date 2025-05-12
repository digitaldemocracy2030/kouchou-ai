import concurrent.futures
import json

import pandas as pd
from tqdm import tqdm

from services.llm import request_to_chat_openai

BASE_CLASSIFICATION_PROMPT = """与えられた意見群をカテゴリに分類してください

# 前提・指示
* 意見は複数与えられることがあります
* 分類対象のカテゴリは複数与えられることがあります
* 前述の前提を踏まえて、出力例に記載したフォーマットでjsonを出力してください

# 分類対象のカテゴリ
{categories_string}

# 出力例
{{
    "arg-id-1": {{
        "カテゴリ1": "カテゴリ1の分類結果",
        "カテゴリ2": "カテゴリ2の分類結果",
    }},
    "arg-id-2": {{
        "カテゴリ1": "カテゴリ1の分類結果",
        "カテゴリ2": "カテゴリ2の分類結果",
    }}
}}


# 分類する意見（id: 内容を記載）
{args_string}
"""

# 構築されるプロンプトの例
# """与えられた意見群をカテゴリに分類してください

# # 前提・指示
# * 意見は複数与えられることがあります
# * 分類対象のカテゴリは複数与えられることがあります
# * 前述の前提を踏まえて、出力例に記載したフォーマットでjsonを出力してください

# # 分類対象のカテゴリ
# それぞれのカテゴリに対して一つづつカテゴリを割り当ててください

# ## カテゴリ: sentiment
# - ポジティブ: 肯定的な意見につけるカテゴリ
# - ネガティブ: 否定的な意見につけるカテゴリ
# - ニュートラル: 中立的な意見につけるカテゴリ

# ## カテゴリ: genre
# - 政治: 政治に関する意見
# - 経済: 経済に関する意見
# - 社会: 社会に関する意見
# - 環境: 環境に関する意見
# - 教育: 教育に関する意見
# - 健康: 健康に関する意見
# - 文化: 文化に関する意見
# - その他: その他

# # 出力例
# {{
#     "arg-id-1": {{
#         "sentiment": "positive",
#         "genre": "politics",
#     }},
#     "arg-id-2": {{
#         "sentiment": "negative",
#         "genre": "economy",
#     }}
# }}


# # 分類する意見（id: 内容を記載）
# - arg-1: 未来の日本では教育に投資してほしい
# - arg-2: 未来の日本では環境に投資してほしい
# """


def _build_categories_string(categories: dict[str, dict[str, str]]) -> str:
    result_string = ""
    for category_type, category_description_dict in categories.items():
        result_string += f"## カテゴリ「{category_type}」の分類先\n"
        for category_description in category_description_dict.items():
            result_string += f"- {category_description}\n"
    return result_string


def _build_batch_args_string(batch_args: pd.DataFrame) -> str:
    return "\n".join(
        [
            f"- {arg_id}: {argument}"
            for arg_id, argument in zip(batch_args["arg-id"], batch_args["argument"], strict=False)
        ]
    )


def _parse_arg_result(classification_results: dict, arg_id: str, categories: list[str]) -> dict:
    def is_valid_category_value(category_value: str) -> bool:
        return isinstance(category_value, str) or isinstance(category_value, bool)

    arg_result = classification_results.get(arg_id, {})
    if not isinstance(arg_result, dict):
        return {"arg-id": arg_id, **dict.fromkeys(categories, None)}

    parsed_result = {"arg-id": arg_id}
    for category in categories:
        category_value = arg_result.get(category, None)
        # カテゴリの値はstrのみを想定（2024/12/19時点）
        parsed_result[category] = category_value if is_valid_category_value(category_value) else None
    return parsed_result


def classify_batch_args(batch_args: pd.DataFrame, categories: dict, model: str) -> dict:
    category_string = _build_categories_string(categories)
    batch_args_string = _build_batch_args_string(batch_args)
    prompt = BASE_CLASSIFICATION_PROMPT.format(categories_string=category_string, args_string=batch_args_string)
    result = request_to_chat_openai(
        messages=[
            {"role": "system", "content": prompt},
        ],
        model=model,
        is_json=True,
    )
    try:
        return json.loads(result)
    except json.JSONDecodeError:
        return {}


def classify_args(args: pd.DataFrame, config, workers: int) -> pd.DataFrame:
    batch_size = config["extraction"]["category_batch_size"]

    classification_results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        batch_start_indices = range(0, len(args), batch_size)
        future_to_batch = {
            executor.submit(
                classify_batch_args,
                args.loc[batch_idx : batch_idx + batch_size],
                config["extraction"]["categories"],
                config["extraction"]["model"],
            ): batch_idx
            for batch_idx in batch_start_indices
        }
        for future in tqdm(
            concurrent.futures.as_completed(future_to_batch),
            total=len(batch_start_indices),
            desc="Classifying arguments",
        ):
            result = future.result()
            classification_results.update(result)

    # 結果をdataframeに変換し、argsにjoinする
    results = []
    categories = list(config["extraction"]["categories"].keys())
    for arg_id in args["arg-id"]:
        arg_result = _parse_arg_result(classification_results, arg_id, categories)
        results.append(arg_result)
    classification_results_df = pd.DataFrame(results)
    merged = args.merge(classification_results_df, on="arg-id", how="left")
    return merged
