"""LLM-driven grouping while preserving embedding-based coordinates for visualization."""

from __future__ import annotations

import json
import os
import pickle
from collections import Counter
from dataclasses import dataclass

import numpy as np
import polars as pl
from pydantic import BaseModel, Field

from analysis_core.services.llm import request_to_chat_ai
from analysis_core.steps.hierarchical_clustering import (
    _load_clustering_dependencies,
    calculate_recommended_cluster_nums,
)

LLM_GROUPING_TIMEOUT_SECONDS = 300


class ProposedGroup(BaseModel):
    """Single discovered group."""

    group_id: str = Field(..., description="Short stable identifier like g1")
    label: str = Field(..., description="Human readable group label")
    description: str = Field(..., description="Explanation of what belongs to the group")


class GroupDiscoveryResponse(BaseModel):
    """Response schema for top-level group discovery."""

    groups: list[ProposedGroup]


class GroupAssignment(BaseModel):
    """Assignment of one argument to one discovered group."""

    arg_id: str = Field(..., description="Argument id from the input batch")
    group_id: str = Field(..., description="One of the discovered group ids")


class GroupAssignmentResponse(BaseModel):
    """Response schema for batch assignments."""

    assignments: list[GroupAssignment]


@dataclass
class GroupDefinition:
    """Normalized discovered group."""

    group_id: str
    label: str
    description: str


def llm_grouping(config: dict) -> None:
    """Generate `hierarchical_clusters.csv` and `hierarchical_merge_labels.csv` via LLM grouping."""
    dataset = config["output_dir"]
    output_base_dir = config.get("_output_base_dir", "outputs")
    args_df = pl.read_csv(f"{output_base_dir}/{dataset}/args.csv", columns=["arg-id", "argument"])
    arg_ids = args_df["arg-id"].to_list()
    arguments = args_df["argument"].to_list()

    llm_config = config["llm_grouping"]
    group_count = _resolve_group_count(config, len(arg_ids))
    groups = _discover_groups(
        arguments=arguments,
        question=config.get("question", ""),
        group_count=group_count,
        sample_size=llm_config.get("discovery_sample_size", 80),
        prompt=llm_config["discovery_prompt"],
        model=llm_config["model"],
        provider=config["provider"],
        local_llm_address=config.get("local_llm_address"),
        config=config,
    )
    assignments = _assign_groups(
        arg_ids=arg_ids,
        arguments=arguments,
        groups=groups,
        batch_size=llm_config.get("assignment_batch_size", 25),
        prompt=llm_config["assignment_prompt"],
        model=llm_config["model"],
        provider=config["provider"],
        local_llm_address=config.get("local_llm_address"),
        config=config,
    )
    points = _project_embeddings_to_xy(output_base_dir, dataset, arg_ids)

    clusters_path = f"{output_base_dir}/{dataset}/hierarchical_clusters.csv"
    merge_labels_path = f"{output_base_dir}/{dataset}/hierarchical_merge_labels.csv"

    cluster_rows = []
    for arg_id, argument, (x, y) in zip(arg_ids, arguments, points, strict=True):
        cluster_rows.append(
            {
                "arg-id": arg_id,
                "argument": argument,
                "x": float(x),
                "y": float(y),
                "cluster-level-1-id": assignments[arg_id],
            }
        )

    pl.DataFrame(cluster_rows).write_csv(clusters_path)
    _write_merge_labels(merge_labels_path, groups, assignments)


def _resolve_group_count(config: dict, argument_count: int) -> int:
    step_config = config.get("llm_grouping", {})
    explicit = step_config.get("group_count")
    if explicit:
        return min(max(1, int(explicit)), max(1, argument_count))

    cluster_nums = config.get("hierarchical_clustering", {}).get("cluster_nums")
    if cluster_nums:
        return min(max(1, int(cluster_nums[0])), max(1, argument_count))

    return calculate_recommended_cluster_nums(max(2, argument_count))[0]


def _discover_groups(
    *,
    arguments: list[str],
    question: str,
    group_count: int,
    sample_size: int,
    prompt: str,
    model: str,
    provider: str,
    local_llm_address: str | None,
    config: dict,
) -> list[GroupDefinition]:
    sample_n = min(len(arguments), max(1, sample_size))
    sample_df = pl.DataFrame({"argument": arguments}).sample(n=sample_n, shuffle=True, seed=0)
    sample_lines = "\n".join(f"- {argument}" for argument in sample_df["argument"].to_list())
    user_message = (
        f"問い:\n{question}\n\n"
        f"以下の意見群を {group_count} 個前後のグループに整理してください。\n"
        "出力する group_id は g1, g2, ... の形式にしてください。\n\n"
        f"{sample_lines}"
    )
    response_text, token_input, token_output, token_total = request_to_chat_ai(
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_message},
        ],
        model=model,
        provider=provider,
        json_schema=GroupDiscoveryResponse,
        local_llm_address=local_llm_address,
        user_api_key=os.getenv("USER_API_KEY"),
        timeout_seconds=LLM_GROUPING_TIMEOUT_SECONDS,
    )
    _accumulate_token_usage(config, token_input, token_output, token_total)
    response_json = json.loads(response_text) if isinstance(response_text, str) else response_text
    raw_groups = response_json.get("groups", [])
    if not raw_groups:
        raise ValueError("llm_grouping group discovery returned no groups")

    normalized_groups = []
    for index, group in enumerate(raw_groups, start=1):
        normalized_groups.append(
            GroupDefinition(
                group_id=f"g{index}",
                label=group.get("label", f"グループ {index}"),
                description=group.get("description", ""),
            )
        )
    return normalized_groups


def _assign_groups(
    *,
    arg_ids: list[str],
    arguments: list[str],
    groups: list[GroupDefinition],
    batch_size: int,
    prompt: str,
    model: str,
    provider: str,
    local_llm_address: str | None,
    config: dict,
) -> dict[str, str]:
    assignments: dict[str, str] = {}
    allowed_group_ids = {group.group_id for group in groups}
    group_text = "\n".join(f"- {group.group_id}: {group.label}\n  {group.description}" for group in groups)

    for start in range(0, len(arg_ids), max(1, batch_size)):
        batch_ids = arg_ids[start : start + batch_size]
        batch_arguments = arguments[start : start + batch_size]
        batch_lines = "\n".join(
            f"- {arg_id}: {argument}" for arg_id, argument in zip(batch_ids, batch_arguments, strict=True)
        )
        user_message = (
            "既知のグループ定義:\n"
            f"{group_text}\n\n"
            "各意見を最も近いグループへ 1 つだけ割り当ててください。\n"
            "新しいグループは作らず、group_id は必ず既知のものから選んでください。\n\n"
            f"意見一覧:\n{batch_lines}"
        )
        response_text, token_input, token_output, token_total = request_to_chat_ai(
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_message},
            ],
            model=model,
            provider=provider,
            json_schema=GroupAssignmentResponse,
            local_llm_address=local_llm_address,
            user_api_key=os.getenv("USER_API_KEY"),
            timeout_seconds=LLM_GROUPING_TIMEOUT_SECONDS,
        )
        _accumulate_token_usage(config, token_input, token_output, token_total)
        response_json = json.loads(response_text) if isinstance(response_text, str) else response_text
        batch_assignments = {
            assignment.get("arg_id"): assignment.get("group_id")
            for assignment in response_json.get("assignments", [])
            if assignment.get("arg_id")
        }

        fallback_group_id = groups[0].group_id
        for arg_id in batch_ids:
            group_id = batch_assignments.get(arg_id, fallback_group_id)
            if group_id not in allowed_group_ids:
                group_id = fallback_group_id
            assignments[arg_id] = group_id

    return assignments


def _project_embeddings_to_xy(output_base_dir: str, dataset: str, arg_ids: list[str]) -> np.ndarray:
    UMAP, _, _ = _load_clustering_dependencies()
    with open(f"{output_base_dir}/{dataset}/embeddings.pkl", "rb") as f:
        embeddings_data = pickle.load(f)

    if isinstance(embeddings_data, list):
        embed_by_id = {item["arg-id"]: item["embedding"] for item in embeddings_data}
        embeddings_array = np.asarray([embed_by_id[arg_id] for arg_id in arg_ids])
    else:
        embeddings_array = np.asarray(embeddings_data["embedding"].values.tolist())

    n_samples = embeddings_array.shape[0]
    n_neighbors = max(2, min(15, n_samples - 1)) if n_samples > 1 else 1
    if n_samples < 2:
        return np.zeros((n_samples, 2))

    umap_model = UMAP(n_components=2, n_neighbors=n_neighbors)
    return umap_model.fit_transform(embeddings_array)


def _write_merge_labels(path: str, groups: list[GroupDefinition], assignments: dict[str, str]) -> None:
    counts = Counter(assignments.values())
    sorted_groups = sorted(groups, key=lambda group: counts.get(group.group_id, 0), reverse=True)
    total_groups = max(1, len(sorted_groups))
    rows = []
    for index, group in enumerate(sorted_groups):
        rows.append(
            {
                "level": 1,
                "id": group.group_id,
                "label": group.label,
                "description": group.description,
                "value": counts.get(group.group_id, 0),
                "parent": "0",
                "density_rank_percentile": (total_groups - index - 1) / max(1, total_groups - 1)
                if total_groups > 1
                else 0.0,
            }
        )
    pl.DataFrame(rows).write_csv(path)


def _accumulate_token_usage(config: dict, token_input: int, token_output: int, token_total: int) -> None:
    config["total_token_usage"] = config.get("total_token_usage", 0) + token_total
    config["token_usage_input"] = config.get("token_usage_input", 0) + token_input
    config["token_usage_output"] = config.get("token_usage_output", 0) + token_output
