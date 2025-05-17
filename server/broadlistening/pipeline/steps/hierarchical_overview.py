"""Create summaries for the clusters."""

import json
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
    response = request_to_chat_ai(
        messages=messages,
        model=model,
        provider=config["provider"],
        local_llm_address=config.get("local_llm_address"),
        json_schema=OverviewResponse,
    )

    try:
        # structured outputとしてパースできるなら処理する
        if isinstance(response, dict):
            parsed_response = response
        else:
            parsed_response = json.loads(response)

        with open(path, "w") as file:
            file.write(parsed_response["summary"])

    except Exception:
        # thinkタグが出力されるReasoningモデル用に、thinkタグを除去する
        thinking_removed = re.sub(
            r"<think\b[^>]*>.*?</think>",
            "",
            response,
            flags=re.DOTALL,
        )

        with open(path, "w") as file:
            file.write(thinking_removed)
