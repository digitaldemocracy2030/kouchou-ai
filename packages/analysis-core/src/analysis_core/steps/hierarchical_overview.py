"""Create summaries for the clusters."""

import json
import os
import re

import polars as pl
from pydantic import BaseModel, Field

from analysis_core.services.llm import _extract_json_text, request_to_chat_ai
from analysis_core.services.timeouts import DEFAULT_REQUEST_TIMEOUT_SECONDS

OVERVIEW_TIMEOUT_SECONDS = DEFAULT_REQUEST_TIMEOUT_SECONDS


class OverviewResponse(BaseModel):
    summary: str = Field(..., description="クラスターの全体的な要約")


def hierarchical_overview(config):
    dataset = config["output_dir"]
    output_base_dir = config.get("_output_base_dir", "outputs")
    path = f"{output_base_dir}/{dataset}/hierarchical_overview.txt"

    hierarchical_label_df = pl.read_csv(f"{output_base_dir}/{dataset}/hierarchical_merge_labels.csv")

    prompt = config["hierarchical_overview"]["prompt"]
    model = config["hierarchical_overview"]["model"]

    # TODO: level1で固定にしているが、設定で変えられるようにする
    target_level = 1
    target_records = hierarchical_label_df.filter(pl.col("level") == target_level)
    ids = target_records["id"].to_list()
    labels = target_records["label"].to_list()
    descriptions = target_records["description"].to_list()

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
        user_api_key=config.get("user_api_key") or os.getenv("USER_API_KEY"),
        json_schema=OverviewResponse,
        timeout_seconds=OVERVIEW_TIMEOUT_SECONDS,
    )

    # トークン使用量を累積
    config["total_token_usage"] = config.get("total_token_usage", 0) + token_total
    config["token_usage_input"] = config.get("token_usage_input", 0) + token_input
    config["token_usage_output"] = config.get("token_usage_output", 0) + token_output
    print(f"Hierarchical overview: input={token_input}, output={token_output}, total={token_total} tokens")

    summary = _extract_summary(response_text)
    with open(path, "w", encoding="utf-8") as file:
        file.write(summary)


def _extract_summary(response_text) -> str:
    """LLM 応答から overview として公開する要約文を取り出す。

    JSON 文字列や途中で切れた JSON を、そのまま overview として公開しない。
    """
    # structured outputとしてパースできるなら処理する
    if isinstance(response_text, dict):
        summary = response_text.get("summary")
        if isinstance(summary, str) and summary.strip():
            return summary
        raise RuntimeError("overview の応答に summary が含まれていません")
    if not isinstance(response_text, str):
        raise RuntimeError(f"overview の応答が文字列ではありません: {type(response_text).__name__}")

    # thinkタグが出力されるReasoningモデル用に、thinkタグを除去する
    thinking_removed = re.sub(
        r"<think\b[^>]*>.*?</think>",
        "",
        response_text,
        flags=re.DOTALL,
    ).strip()

    try:
        parsed_response = json.loads(_extract_json_text(thinking_removed))
    except (TypeError, ValueError):
        parsed_response = None
    if isinstance(parsed_response, dict):
        summary = parsed_response.get("summary")
        if isinstance(summary, str) and summary.strip():
            return summary
        raise RuntimeError("overview の応答に summary が含まれていません")

    # JSON を返さず要約文だけを返すモデル向けに、JSON らしくない本文はそのまま使う。
    # 空の応答や途中で切れた JSON は公開しない。
    if not thinking_removed or thinking_removed.startswith(("{", "[", "```")):
        raise RuntimeError("overview の応答から summary を取り出せませんでした")
    return thinking_removed
