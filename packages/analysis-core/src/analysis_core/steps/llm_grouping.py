"""LLM-driven grouping while preserving embedding-based coordinates for visualization."""

from __future__ import annotations

import json
import os
from collections import Counter
from concurrent.futures import FIRST_EXCEPTION, ThreadPoolExecutor, wait
from dataclasses import dataclass

import numpy as np
import polars as pl
from pydantic import BaseModel, Field

from analysis_core.services.llm import request_to_chat_ai
from analysis_core.services.timeouts import DEFAULT_REQUEST_TIMEOUT_SECONDS
from analysis_core.steps._embeddings_io import load_embeddings_pickle, stack_embedding_rows
from analysis_core.steps.hierarchical_clustering import (
    MIN_ARGUMENTS_FOR_UMAP_FIT,
    UMAP_N_COMPONENTS,
    _load_clustering_dependencies,
    calculate_recommended_cluster_nums,
)

# グループ発見・割当の LLM 呼び出しも、ほかの工程と同じく LLM_REQUEST_TIMEOUT_SECONDS に従う
LLM_GROUPING_TIMEOUT_SECONDS = DEFAULT_REQUEST_TIMEOUT_SECONDS

# 指定カテゴリ分類（supervised）で必ず用意する「その他」受け皿。
# どのカテゴリにも当てはまらない意見を無理に押し込めないための catch-all。
_OTHER_GROUP_ID = "other"
_DEFAULT_OTHER_LABEL = "その他"
_DEFAULT_OTHER_DESCRIPTION = "指定したどのカテゴリにも明確に当てはまらない意見"


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
    predefined_groups = _resolve_predefined_groups(llm_config)
    if predefined_groups is not None:
        # 指定カテゴリ分類（supervised）: 枠は人間が与え、割当だけ LLM に任せる。
        # 発見段（_discover_groups）はスキップし、必ず「その他」受け皿を足す。
        groups, other_group_id = _ensure_other_group(predefined_groups, llm_config)
    else:
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
        other_group_id = None
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
        other_group_id=other_group_id,
        workers=_resolve_workers(llm_config),
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


def _resolve_workers(llm_config: dict) -> int:
    """割当の同時実行数。未指定・None（旧 config の書き戻しなど）は 1（直列）にする。"""
    try:
        return max(1, int(llm_config.get("workers") or 1))
    except (TypeError, ValueError):
        return 1


def _resolve_predefined_groups(llm_config: dict) -> list[GroupDefinition] | None:
    """`predefined_groups` を正規化する。未指定（falsy）なら None（＝自動グルーピング）。

    各要素は ``{"id"?, "label", "description"?}`` の dict、または label 文字列。
    label 必須・id 重複不可。「その他」受け皿はここでは足さない（_ensure_other_group の責務）。
    """
    raw_groups = llm_config.get("predefined_groups")
    if not raw_groups:
        return None
    if not isinstance(raw_groups, (list, tuple)):
        raise ValueError("predefined_groups must be a list of category definitions")

    groups: list[GroupDefinition] = []
    seen_ids: set[str] = set()
    for index, item in enumerate(raw_groups, start=1):
        if isinstance(item, str):
            label, description, raw_id = item, "", None
        elif isinstance(item, dict):
            label = str(item.get("label") or "").strip()
            description = str(item.get("description") or "").strip()
            raw_id = item.get("id")
        else:
            raise ValueError("predefined_groups: each entry must be a string or an object")

        if not label:
            raise ValueError("predefined_groups: each category requires a non-empty label")

        group_id = str(raw_id).strip() if raw_id not in (None, "") else f"g{index}"
        if group_id in seen_ids:
            raise ValueError(f"predefined_groups: duplicate group id '{group_id}'")
        seen_ids.add(group_id)
        groups.append(GroupDefinition(group_id=group_id, label=label, description=description))

    return groups


def _ensure_other_group(groups: list[GroupDefinition], llm_config: dict) -> tuple[list[GroupDefinition], str]:
    """指定カテゴリに必ず「その他」受け皿を用意し、(groups, other_group_id) を返す。

    既にユーザが同等の受け皿（id が ``other`` もしくは label が「その他」ラベル）を
    定義していればそれを流用し、二重には足さない。
    """
    other_label = str(llm_config.get("other_group_label") or _DEFAULT_OTHER_LABEL).strip() or _DEFAULT_OTHER_LABEL
    for group in groups:
        if group.group_id == _OTHER_GROUP_ID or group.label == other_label:
            return groups, group.group_id

    other_group = GroupDefinition(
        group_id=_OTHER_GROUP_ID,
        label=other_label,
        description=_DEFAULT_OTHER_DESCRIPTION,
    )
    return [*groups, other_group], _OTHER_GROUP_ID


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
        user_api_key=config.get("user_api_key") or os.getenv("USER_API_KEY"),
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
    other_group_id: str | None = None,
    workers: int = 1,
) -> dict[str, str]:
    """意見を batch_size 件ずつのバッチに分け、各バッチの割当を LLM に問い合わせる。

    バッチは最大 workers 本を同時に呼ぶ。結果はバッチの順に集めるので、返す dict の順序と
    arg_id → group_id の対応は直列で呼んだ場合と変わらない。トークン数の加算も呼び出し元の
    スレッドで行う。

    失敗は完了順に検知する。どれかのバッチが失敗した時点で、まだ始まっていないバッチは取り消して
    送らない（先頭側のバッチが遅れていても、その完了を待たずに止める）。ただし、その時点で実行中の
    呼び出しは止められないので、それらが終わるのを待ってから例外を伝える（最長で LLM 呼び出しの
    タイムアウトと再試行の分）。送って成功したバッチのトークン数は、失敗した場合も計上する。
    """
    allowed_group_ids = {group.group_id for group in groups}
    group_text = "\n".join(f"- {group.group_id}: {group.label}\n  {group.description}" for group in groups)

    # 指定カテゴリ分類では、非該当・無効応答を先頭枠ではなく「その他」へ寄せる。
    fallback_group_id = other_group_id if other_group_id in allowed_group_ids else groups[0].group_id
    other_instruction = ""
    if other_group_id in allowed_group_ids:
        other_label = next((group.label for group in groups if group.group_id == other_group_id), other_group_id)
        other_instruction = (
            f"どのグループにも明確に当てはまらない意見は、無理に分類せず "
            f"『{other_label}』({other_group_id}) に割り当ててください。\n"
        )

    def assign_batch(batch_ids: list[str], batch_arguments: list[str]) -> tuple[dict, int, int, int]:
        batch_lines = "\n".join(
            f"- {arg_id}: {argument}" for arg_id, argument in zip(batch_ids, batch_arguments, strict=True)
        )
        user_message = (
            "既知のグループ定義:\n"
            f"{group_text}\n\n"
            "各意見を最も近いグループへ 1 つだけ割り当ててください。\n"
            "新しいグループは作らず、group_id は必ず既知のものから選んでください。\n"
            f"{other_instruction}\n"
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
            user_api_key=config.get("user_api_key") or os.getenv("USER_API_KEY"),
            timeout_seconds=LLM_GROUPING_TIMEOUT_SECONDS,
        )
        response_json = json.loads(response_text) if isinstance(response_text, str) else response_text
        batch_assignments = {
            assignment.get("arg_id"): assignment.get("group_id")
            for assignment in response_json.get("assignments", [])
            if assignment.get("arg_id")
        }
        return batch_assignments, token_input, token_output, token_total

    safe_batch_size = max(1, batch_size)
    batches = [
        (arg_ids[start : start + safe_batch_size], arguments[start : start + safe_batch_size])
        for start in range(0, len(arg_ids), safe_batch_size)
    ]
    if not batches:
        return {}

    with ThreadPoolExecutor(max_workers=max(1, min(workers, len(batches)))) as executor:
        futures = [executor.submit(assign_batch, batch_ids, batch_arguments) for batch_ids, batch_arguments in batches]
        try:
            # 完了順に失敗を見る。バッチ順に result() を待つと、先頭のバッチが遅い間に
            # 後ろのバッチの失敗に気づけず、残りのバッチを送り続けてしまう。
            _, not_done = wait(futures, return_when=FIRST_EXCEPTION)
        except BaseException:
            for future in futures:
                future.cancel()
            raise
        # 失敗があれば、まだ始まっていないバッチは送らない（課金と待ち時間を増やさない）
        for future in not_done:
            future.cancel()
    # with を抜けた時点で、実行中だった呼び出しも終わっている

    failure: BaseException | None = None
    results: list[tuple[dict, int, int, int] | None] = []
    for future in futures:
        if future.cancelled():
            results.append(None)
            continue
        error = future.exception()
        if error is not None:
            failure = failure or error
            results.append(None)
            continue
        batch_result = future.result()
        # 送って成功したバッチは課金されているので、失敗した場合も計上する
        _accumulate_token_usage(config, *batch_result[1:])
        results.append(batch_result)
    if failure is not None:
        raise failure

    assignments: dict[str, str] = {}
    for (batch_ids, _), batch_result in zip(batches, results, strict=True):
        batch_assignments = batch_result[0]
        for arg_id in batch_ids:
            group_id = batch_assignments.get(arg_id, fallback_group_id)
            if group_id not in allowed_group_ids:
                group_id = fallback_group_id
            assignments[arg_id] = group_id
    return assignments


def _project_embeddings_to_xy(output_base_dir: str, dataset: str, arg_ids: list[str]) -> np.ndarray:
    UMAP, _, _ = _load_clustering_dependencies()
    embeddings_data = load_embeddings_pickle(f"{output_base_dir}/{dataset}/embeddings.pkl")

    if isinstance(embeddings_data, list):
        embed_by_id = {}
        for index, item in enumerate(embeddings_data):
            item_arg_id = item.get("arg-id") if isinstance(item, dict) else None
            if item_arg_id is None and index < len(arg_ids):
                item_arg_id = arg_ids[index]
            if item_arg_id is None:
                continue
            embed_by_id[item_arg_id] = item["embedding"]
        item = None  # ループ変数が最後の要素（の埋め込み）を参照し続けないようにする

        missing_arg_ids = [arg_id for arg_id in arg_ids if arg_id not in embed_by_id]
        if missing_arg_ids:
            raise ValueError(f"Missing embeddings for arg ids: {missing_arg_ids}")

        embeddings_array = stack_embedding_rows([embed_by_id[arg_id] for arg_id in arg_ids])
        del embed_by_id
    else:
        embeddings_array = stack_embedding_rows(embeddings_data["embedding"].values.tolist())
    # 読み込んだ list / dict を UMAP の前に解放する（hierarchical_clustering と同じ理由）
    del embeddings_data

    n_samples = embeddings_array.shape[0]
    if n_samples < 2:
        return np.zeros((n_samples, UMAP_N_COMPONENTS))
    if n_samples < MIN_ARGUMENTS_FOR_UMAP_FIT:
        # 2〜3 件では UMAP の fit がライブラリ内部のエラーで落ちる。グループの割当はもう済んでいて、
        # 座標は散布図の表示に使うだけなので、点が重ならないよう円周上に並べる
        angles = 2 * np.pi * np.arange(n_samples) / n_samples
        return np.column_stack([np.cos(angles), np.sin(angles)])

    n_neighbors = max(2, min(15, n_samples - 1))
    umap_model = UMAP(n_components=UMAP_N_COMPONENTS, n_neighbors=n_neighbors)
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
