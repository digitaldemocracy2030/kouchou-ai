import json
import shutil
from typing import Literal

import polars as pl
from pydantic import BaseModel, Field

from analysis_core.services.llm import request_to_chat_ai


class RefinedClusterLabel(BaseModel):
    cluster_id: str = Field(..., description="Refined target cluster id")
    label: str = Field(..., description="Short top-level label")
    description: str = Field(..., description="Representative cluster description")


class RefinedClusterSet(BaseModel):
    clusters: list[RefinedClusterLabel]


def hierarchical_label_refinement(config: dict) -> None:
    dataset = config["output_dir"]
    output_base_dir = config.get("_output_base_dir", "outputs")
    labels_path = f"{output_base_dir}/{dataset}/hierarchical_merge_labels.csv"
    backup_path = f"{output_base_dir}/{dataset}/hierarchical_merge_labels.original.csv"
    refined_path = f"{output_base_dir}/{dataset}/hierarchical_refined_labels.csv"

    labels_df = pl.read_csv(labels_path)
    step_config = config.get("hierarchical_label_refinement", {})
    mode = step_config.get("mode", "none")

    if mode == "none":
        labels_df.write_csv(refined_path)
        return

    if not step_config.get("prompt"):
        raise ValueError("hierarchical_label_refinement.prompt is required when mode is enabled")

    if labels_df.filter(pl.col("level") == 1).height == 0:
        labels_df.write_csv(refined_path)
        return

    refined_level1 = _refine_level1_labels(labels_df, config, step_config)
    refined_df = labels_df.join(refined_level1, on="id", how="left")
    refined_df = refined_df.with_columns(
        pl.when(pl.col("refined_label").is_not_null())
        .then(pl.col("refined_label"))
        .otherwise(pl.col("label"))
        .alias("label"),
        pl.when(pl.col("refined_description").is_not_null())
        .then(pl.col("refined_description"))
        .otherwise(pl.col("description"))
        .alias("description"),
    ).drop(["refined_label", "refined_description"])

    shutil.copyfile(labels_path, backup_path)
    refined_df.write_csv(labels_path)
    refined_df.write_csv(refined_path)


def _refine_level1_labels(labels_df: pl.DataFrame, config: dict, step_config: dict) -> pl.DataFrame:
    level1_rows = labels_df.filter(pl.col("level") == 1).sort("id")
    child_rows = labels_df.filter(pl.col("level") > 1)
    sibling_sections = []

    for row in level1_rows.iter_rows(named=True):
        sibling_sections.append(_build_cluster_section(row, child_rows))

    messages = [
        {"role": "system", "content": "あなたは意見分析の編集者です。クラスタ集合全体を見て、読みやすく区別しやすい見出しへ整えてください。"},
        {
            "role": "user",
            "content": step_config["prompt"].format(
                mode=step_config.get("mode", "none"),
                max_label_length=step_config.get("max_label_length", 24),
                cluster_set="\n\n".join(sibling_sections),
            ),
        },
    ]

    response, token_in, token_out, token_total = request_to_chat_ai(
        messages=messages,
        model=step_config.get("model", config.get("model", "gpt-4o-mini")),
        json_schema=RefinedClusterSet,
        provider=config.get("provider", "openai"),
        local_llm_address=config.get("local_llm_address"),
        user_api_key=config.get("user_api_key"),
    )
    parsed = response if isinstance(response, dict) else json.loads(response)
    refined = RefinedClusterSet.model_validate(parsed)
    config["token_usage_input"] = config.get("token_usage_input", 0) + token_in
    config["token_usage_output"] = config.get("token_usage_output", 0) + token_out
    config["total_token_usage"] = config.get("total_token_usage", 0) + token_total

    refined_by_id = {
        item.cluster_id: {
            "id": item.cluster_id,
            "refined_label": item.label,
            "refined_description": item.description,
        }
        for item in refined.clusters
    }
    missing_ids = set(level1_rows["id"].to_list()) - set(refined_by_id.keys())
    if missing_ids:
        raise ValueError(f"Missing refined labels for cluster ids: {sorted(missing_ids)}")

    return pl.DataFrame(list(refined_by_id.values()))


def _build_cluster_section(row: dict, child_rows: pl.DataFrame) -> str:
    cluster_id = str(row["id"])
    child_summaries = (
        child_rows.filter(pl.col("parent") == cluster_id)
        .sort("id")
        .select(["id", "label", "description", "value"])
        .iter_rows(named=True)
    )
    child_lines = [
        f"- child {child['id']} ({child['value']}): {child['label']} / {child['description']}"
        for child in child_summaries
    ]
    if not child_lines:
        child_lines = ["- child none"]

    return "\n".join(
        [
            f"cluster_id: {cluster_id}",
            f"current_label: {row['label']}",
            f"current_description: {row['description']}",
            f"size: {row['value']}",
            "children:",
            *child_lines,
        ]
    )


def build_refinement_prompt(mode: Literal["setwise_refine", "setwise_refine_short"] | str, max_label_length: int) -> str:
    short_constraint = ""
    if mode == "setwise_refine_short":
        short_constraint = (
            f"- label はできるだけ短く、目安として {max_label_length} 文字以内にしてください\n"
            "- 見出しとして一覧で並んだ時に scan しやすい表現にしてください\n"
        )

    return """以下は top-level cluster 群です。cluster 集合全体を見て、各 cluster の label と description を再作成してください。

# 目的
- 各 cluster が何を代表しているかを保つ
- sibling 同士の違いが見えるようにする
- 粒度を揃える
- 似た言い回しや重複を減らす

# 指示
- すべての cluster_id をそのまま維持してください
- 各 cluster について label と description を返してください
- label は current_label をそのまま焼き直すのではなく、内容に基づいて書き換えてください
- description は代表性を保ちつつ、隣接 cluster との差も伝わるようにしてください
{short_constraint}
- JSON だけを返してください

入力:
{cluster_set}
""".replace("{short_constraint}", short_constraint)
