"""Create summaries for the clusters."""

import json
import os
import re

import pandas as pd
from pydantic import BaseModel, Field

from services.llm import request_to_chat_ai


class OverviewResponse(BaseModel):
    summary: str = Field(..., description="クラスターの全体的な要約")


def hierarchical_overview(config):
    dataset = config["output_dir"]
    path = f"outputs/{dataset}/hierarchical_overview.txt"

    hierarchical_label_df = pd.read_csv(f"outputs/{dataset}/hierarchical_merge_labels.csv")

    prompt = config["hierarchical_overview"]["prompt"]
    model = config["hierarchical_overview"]["model"]

    # TODO: level1で固定にしているが、設定で変えられるようにする
    target_level = 1
    target_records = hierarchical_label_df[hierarchical_label_df["level"] == target_level]
    ids = target_records["id"].to_list()
    labels = target_records["label"].to_list()
    descriptions = target_records["description"].to_list()
    target_records.set_index("id", inplace=True)

    input_text = ""
    for i, _ in enumerate(ids):
        input_text += f"# Cluster {i}/{len(ids)}: {labels[i]}\n\n"
        input_text += descriptions[i] + "\n\n"

    messages = [{"role": "system", "content": prompt}, {"role": "user", "content": input_text}]
    response_text, token_input, token_output, token_total = request_to_chat_ai(
        messages=messages,
        model=model,
        provider=config["provider"],
        local_llm_address=config.get("local_llm_address"),
        user_api_key=os.getenv("USER_API_KEY"),
        json_schema=OverviewResponse,
    )

    # トークン使用量を累積
    config["total_token_usage"] = config.get("total_token_usage", 0) + token_total
    config["token_usage_input"] = config.get("token_usage_input", 0) + token_input
    config["token_usage_output"] = config.get("token_usage_output", 0) + token_output
    print(f"Hierarchical overview: input={token_input}, output={token_output}, total={token_total} tokens")

    try:
        # structured outputとしてパースできるなら処理する
        if isinstance(response_text, dict):
            parsed_response = response_text
        else:
            parsed_response = json.loads(response_text)

        with open(path, "w") as file:
            file.write(parsed_response["summary"])

    except Exception:
        # thinkタグが出力されるReasoningモデル用に、thinkタグを除去する
        thinking_removed = re.sub(
            r"<think\b[^>]*>.*?</think>",
            "",
            response_text,
            flags=re.DOTALL,
        )

        with open(path, "w") as file:
            file.write(thinking_removed)
