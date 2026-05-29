import argparse
import json
import sys
from pathlib import Path
from typing import Any, Literal

# このスクリプトから repo 直下の analysis-core/src を PYTHONPATH に追加
root_path = Path(__file__).resolve().parents[3] / "packages" / "analysis-core" / "src"
sys.path.insert(0, str(root_path))

import pandas as pd  # noqa: E402
from analysis_core.services.llm import request_to_chat_ai  # noqa: E402
from pydantic import BaseModel, Field  # noqa: E402


RUBRIC_VERSION = "label-quality-v0"


CLUSTER_CRITERIA = [
    {
        "id": "COV_MAIN_TOPIC",
        "axis": "coverage",
        "points": 20,
        "criterion": "ラベルが、提示された意見群で最も中心的な論点を含んでいる",
    },
    {
        "id": "COV_TOP_AXES",
        "axis": "coverage",
        "points": 15,
        "criterion": "クラスタが複数軸を含む場合、上位2〜3軸がラベルまたは説明に出ている",
    },
    {
        "id": "GROUND_LABEL",
        "axis": "grounding",
        "points": 15,
        "criterion": "ラベルの主要語が、提示された意見または子クラスタのラベル・説明から根拠づけられる",
    },
    {
        "id": "DESC_BOUNDARY",
        "axis": "description",
        "points": 10,
        "criterion": "説明がクラスタの担当範囲を補い、ラベルだけでは落ちる論点を補っている",
    },
    {
        "id": "DIST_SIBLING",
        "axis": "distinctiveness",
        "points": 10,
        "criterion": "sibling label 一覧と比べて、このラベルの担当範囲が区別できる",
    },
    {
        "id": "SCAN_LENGTH",
        "axis": "scanability",
        "points": 5,
        "criterion": "ラベルが一覧UIでscan可能な長さに収まり、汎用接頭辞だけで差分を隠していない",
    },
    {
        "id": "REGISTER_OK",
        "axis": "register",
        "points": 5,
        "criterion": "public / policy 文脈で不自然な口語・過度なmarketing語になっていない",
    },
    {
        "id": "UNSUPPORTED_AXIS",
        "axis": "grounding",
        "points": -25,
        "criterion": "ラベルが、提示された材料から確認できない重要軸を主張している",
        "fatal_flag": "unsupported_axis",
    },
    {
        "id": "MISSING_VISIBLE_AXIS",
        "axis": "coverage",
        "points": -20,
        "criterion": "提示された材料に明確な重要軸があるのに、ラベル・説明の両方から落ちている",
        "fatal_flag": "missing_visible_axis",
    },
    {
        "id": "DUPLICATE_SIBLING",
        "axis": "distinctiveness",
        "points": -15,
        "criterion": "sibling と意味が大きく重なり、ユーザーがどちらを開くべきか判断しにくい",
        "fatal_flag": "duplicate_sibling",
    },
    {
        "id": "GENERIC_BUCKET",
        "axis": "specificity",
        "points": -10,
        "criterion": "具体的な論点があるのに『AI活用』『社会課題』などの汎用bucketに逃げている",
    },
]


LABEL_SET_CRITERIA = [
    {
        "id": "SET_DISTINCT_HEADINGS",
        "axis": "distinctiveness",
        "points": 15,
        "criterion": "主要ラベルが、先頭数語だけ見ても互いに区別できる",
    },
    {
        "id": "SET_GRANULARITY",
        "axis": "granularity",
        "points": 10,
        "criterion": "ラベル間で粒度が大きくずれていない",
    },
    {
        "id": "SET_COVERAGE",
        "axis": "coverage",
        "points": 15,
        "criterion": "top-level label set が、提示されたクラスタ群の主要テーマを概ね覆っている",
    },
    {
        "id": "SET_NO_PREFIX_NOISE",
        "axis": "scanability",
        "points": 5,
        "criterion": "共通接頭辞が差分理解を邪魔していない",
    },
    {
        "id": "SET_REGISTER_CONSISTENT",
        "axis": "register",
        "points": 5,
        "criterion": "label set 全体で語調が揃っている",
    },
    {
        "id": "SET_DUPLICATE_PAIR",
        "axis": "distinctiveness",
        "points": -20,
        "criterion": "ほぼ同じ意味の label pair がある",
        "fatal_flag": "set_duplicate_pair",
    },
    {
        "id": "SET_HIDDEN_RESIDUAL",
        "axis": "coverage",
        "points": -15,
        "criterion": "大きなクラスタの重要テーマが label set 上で見えなくなっている",
        "fatal_flag": "set_hidden_residual",
    },
]


class RubricCriterionResult(BaseModel):
    id: str = Field(..., description="Criterion id from the supplied rubric")
    criteria_met: bool = Field(..., description="Whether the criterion is met")
    rationale: str = Field(..., description="Short reason based only on the shown evidence")
    evidence: list[str] = Field(default_factory=list, description="Short quoted or paraphrased evidence")


class ClusterRubricResponse(BaseModel):
    cluster_id: str
    criteria_results: list[RubricCriterionResult]
    comment: str = Field(..., description="Short overall comment and suggested improvement")


class LabelSetRubricResponse(BaseModel):
    criteria_results: list[RubricCriterionResult]
    comment: str = Field(..., description="Short overall label-set comment and suggested improvement")


def _criteria_map(criteria: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {str(item["id"]): item for item in criteria}


def _positive_max_score(criteria: list[dict[str, Any]]) -> int:
    return sum(int(item["points"]) for item in criteria if int(item["points"]) > 0)


def _score_to_5(score_rate: float) -> int:
    clamped = min(max(score_rate, 0.0), 1.0)
    return int(round(1 + clamped * 4))


def score_criteria_results(
    raw_results: list[RubricCriterionResult],
    criteria: list[dict[str, Any]],
) -> dict[str, Any]:
    criteria_by_id = _criteria_map(criteria)
    raw_by_id = {result.id: result for result in raw_results}
    normalized = []
    fatal_flags = []
    raw_score = 0

    for criterion in criteria:
        criterion_id = str(criterion["id"])
        result = raw_by_id.get(criterion_id)
        criteria_met = bool(result.criteria_met) if result else False
        points = int(criterion["points"])
        signed_score = points if criteria_met else 0
        raw_score += signed_score

        if criteria_met and criterion.get("fatal_flag"):
            fatal_flags.append(str(criterion["fatal_flag"]))

        normalized.append(
            {
                "id": criterion_id,
                "axis": criterion["axis"],
                "points": points,
                "criteria_met": criteria_met,
                "signed_score": signed_score,
                "criterion": criterion["criterion"],
                "rationale": result.rationale if result else "LLM response did not include this criterion.",
                "evidence": result.evidence if result else [],
            }
        )

    unknown = [
        result.model_dump()
        for result in raw_results
        if result.id not in criteria_by_id
    ]
    max_score = _positive_max_score(criteria)
    score_rate = raw_score / max_score if max_score else 0.0
    return {
        "score": raw_score,
        "max_score": max_score,
        "score_rate": round(score_rate, 4),
        "score_5": _score_to_5(score_rate),
        "fatal_flags": fatal_flags,
        "criteria_results": normalized,
        "unknown_criteria_results": unknown,
    }


def _format_criteria(criteria: list[dict[str, Any]]) -> str:
    lines = []
    for item in criteria:
        polarity = "positive" if int(item["points"]) > 0 else "negative"
        lines.append(
            f"- {item['id']} ({item['axis']}, {polarity}, {item['points']} pts): {item['criterion']}"
        )
    return "\n".join(lines)


def _format_arguments(arguments: list[str]) -> str:
    if not arguments:
        return "- no arguments were supplied"
    return "\n".join(f"- {arg}" for arg in arguments)


def _format_sibling_labels(siblings: list[dict[str, Any]]) -> str:
    if not siblings:
        return "- no sibling labels were supplied"
    return "\n".join(
        f"- {item['cluster_id']} ({item['size']}): {item['label']} / {item['description']}"
        for item in siblings
    )


def build_cluster_prompt(cluster_id: str, data: dict[str, Any]) -> str:
    return f"""あなたは広聴AIのクラスタラベル品質を評価する judge です。

# 判定方針
- 各 criterion を true / false で判定してください。
- positive criterion は満たしていれば true、満たしていなければ false。
- negative criterion は問題が実際に見える場合だけ true。問題が見えない場合は false。
- 提示された材料だけを根拠にしてください。材料にないことを推測して補わないでください。
- スコア計算は呼び出し側で行うため、criteria_met / rationale / evidence だけを返してください。

# Rubric
{_format_criteria(CLUSTER_CRITERIA)}

# Output JSON
すべての criterion id を1回ずつ含め、JSONだけを返してください。
例:
{{
  "cluster_id": "{cluster_id}",
  "criteria_results": [
    {{
      "id": "COV_MAIN_TOPIC",
      "criteria_met": true,
      "rationale": "提示された意見の中心論点をラベルが含んでいるため。",
      "evidence": ["根拠になる意見または要約"]
    }}
  ],
  "comment": "全体コメントと改善案"
}}

# Target cluster
cluster_id: {cluster_id}
label: {data["label"]}
description: {data["description"]}
size: {data["size"]}

# Sibling labels
{_format_sibling_labels(data["siblings"])}

# Shown arguments
{_format_arguments(data["arguments"])}
"""


def build_label_set_prompt(cluster_data: dict[str, dict[str, Any]]) -> str:
    sections = []
    for cluster_id, data in cluster_data.items():
        sections.append(
            "\n".join(
                [
                    f"cluster_id: {cluster_id}",
                    f"label: {data['label']}",
                    f"description: {data['description']}",
                    f"size: {data['size']}",
                    "shown_arguments:",
                    _format_arguments(data["arguments"]),
                ]
            )
        )
    cluster_set_text = "\n\n---\n\n".join(sections)

    return f"""あなたは広聴AIの top-level label set 品質を評価する judge です。

# 判定方針
- label set 全体を見て、各 criterion を true / false で判定してください。
- positive criterion は満たしていれば true、満たしていなければ false。
- negative criterion は問題が実際に見える場合だけ true。問題が見えない場合は false。
- 提示された材料だけを根拠にしてください。
- スコア計算は呼び出し側で行うため、criteria_met / rationale / evidence だけを返してください。

# Rubric
{_format_criteria(LABEL_SET_CRITERIA)}

# Output JSON
すべての criterion id を1回ずつ含め、JSONだけを返してください。
例:
{{
  "criteria_results": [
    {{
      "id": "SET_DISTINCT_HEADINGS",
      "criteria_met": true,
      "rationale": "主要ラベルの先頭語が十分に異なるため。",
      "evidence": ["根拠になるラベル名"]
    }}
  ],
  "comment": "label set 全体コメントと改善案"
}}

# Cluster set
{cluster_set_text}
"""


def _parse_response(response: Any, model_cls: type[BaseModel]) -> BaseModel:
    if isinstance(response, dict):
        return model_cls.model_validate(response)
    if isinstance(response, str):
        return model_cls.model_validate(json.loads(response))
    raise TypeError(f"Unsupported LLM response type: {type(response).__name__}")


def evaluate_cluster(
    cluster_id: str,
    data: dict[str, Any],
    *,
    model: str,
    provider: str,
    local_llm_address: str | None,
) -> tuple[dict[str, Any], int, int, int]:
    messages = [
        {"role": "system", "content": "あなたは出力品質を厳密に点検する評価者です。"},
        {"role": "user", "content": build_cluster_prompt(cluster_id, data)},
    ]
    response, token_in, token_out, token_total = request_to_chat_ai(
        messages=messages,
        model=model,
        json_schema=ClusterRubricResponse,
        provider=provider,
        local_llm_address=local_llm_address,
    )
    parsed = _parse_response(response, ClusterRubricResponse)
    scored = score_criteria_results(parsed.criteria_results, CLUSTER_CRITERIA)
    return (
        {
            "rubric_version": RUBRIC_VERSION,
            "cluster_id": parsed.cluster_id,
            "label": data["label"],
            "description": data["description"],
            "comment": parsed.comment,
            **scored,
        },
        token_in,
        token_out,
        token_total,
    )


def evaluate_label_set(
    cluster_data: dict[str, dict[str, Any]],
    *,
    model: str,
    provider: str,
    local_llm_address: str | None,
) -> tuple[dict[str, Any], int, int, int]:
    messages = [
        {"role": "system", "content": "あなたは出力品質を厳密に点検する評価者です。"},
        {"role": "user", "content": build_label_set_prompt(cluster_data)},
    ]
    response, token_in, token_out, token_total = request_to_chat_ai(
        messages=messages,
        model=model,
        json_schema=LabelSetRubricResponse,
        provider=provider,
        local_llm_address=local_llm_address,
    )
    parsed = _parse_response(response, LabelSetRubricResponse)
    scored = score_criteria_results(parsed.criteria_results, LABEL_SET_CRITERIA)
    return (
        {
            "rubric_version": RUBRIC_VERSION,
            "comment": parsed.comment,
            **scored,
        },
        token_in,
        token_out,
        token_total,
    )


def _allocate_argument_budget(
    all_args: dict[str, list[str]],
    max_samples: int,
    sample_mode: Literal["all", "head", "proportional"],
) -> dict[str, list[str]]:
    if sample_mode == "all" or max_samples <= 0:
        return all_args

    total_clusters = len(all_args)
    total_items = sum(len(items) for items in all_args.values())
    if total_items <= max_samples:
        return all_args
    if max_samples < total_clusters:
        raise ValueError(f"max-samples({max_samples}) is less than number of clusters({total_clusters})")

    if sample_mode == "head":
        per_cluster = max(1, max_samples // total_clusters)
        return {cid: items[:per_cluster] for cid, items in all_args.items()}

    remaining_budget = max_samples - total_clusters
    sampled: dict[str, list[str]] = {}
    for cid, items in all_args.items():
        ratio = len(items) / total_items if total_items else 0
        extra = int(ratio * remaining_budget)
        count = min(len(items), 1 + extra)
        sampled[cid] = items[:count]
    return sampled


def load_cluster_data(
    dataset_path: Path,
    level: int,
    max_samples: int,
    sample_mode: Literal["all", "head", "proportional"],
) -> dict[str, dict[str, Any]]:
    labels_df = pd.read_csv(dataset_path / "hierarchical_merge_labels.csv")
    clusters_df = pd.read_csv(dataset_path / "hierarchical_clusters.csv")

    cluster_col = f"cluster-level-{level}-id"
    if cluster_col not in clusters_df.columns:
        raise KeyError(f"{cluster_col} column is missing from hierarchical_clusters.csv")

    level_labels = labels_df[labels_df["level"] == level].copy()
    level_labels["id"] = level_labels["id"].astype(str)
    level_labels = level_labels.sort_values("id")

    all_args = {}
    for _, row in level_labels.iterrows():
        cluster_id = str(row["id"])
        cluster_args = clusters_df[clusters_df[cluster_col].astype(str) == cluster_id]["argument"].tolist()
        all_args[cluster_id] = cluster_args

    sampled_args = _allocate_argument_budget(all_args, max_samples, sample_mode)
    siblings = [
        {
            "cluster_id": str(row["id"]),
            "label": row["label"],
            "description": row["description"],
            "size": int(row["value"]),
        }
        for _, row in level_labels.iterrows()
    ]

    cluster_data = {}
    for _, row in level_labels.iterrows():
        cluster_id = str(row["id"])
        cluster_data[cluster_id] = {
            "label": row["label"],
            "description": row["description"],
            "size": int(row["value"]),
            "arguments": sampled_args.get(cluster_id, []),
            "siblings": siblings,
        }
    return cluster_data


def summarize_results(results: dict[str, dict[str, Any]], label_set_result: dict[str, Any] | None) -> dict[str, Any]:
    cluster_entries = [entry for entry in results.values() if isinstance(entry, dict)]
    score_rates = [
        entry.get("score_rate")
        for entry in cluster_entries
        if isinstance(entry.get("score_rate"), (int, float))
    ]
    fatal_clusters = [
        entry["cluster_id"]
        for entry in cluster_entries
        if entry.get("fatal_flags")
    ]
    return {
        "cluster_count": len(cluster_entries),
        "average_score_rate": round(sum(score_rates) / len(score_rates), 4) if score_rates else None,
        "average_score_5": _score_to_5(sum(score_rates) / len(score_rates)) if score_rates else None,
        "fatal_cluster_count": len(fatal_clusters),
        "fatal_clusters": fatal_clusters,
        "label_set_score_rate": label_set_result.get("score_rate") if label_set_result else None,
        "label_set_fatal_flags": label_set_result.get("fatal_flags") if label_set_result else [],
    }


def save_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"✓ 結果を保存しました: {path}")


def save_prompts(cluster_data: dict[str, dict[str, Any]], output_path: Path) -> None:
    parts = ["# Label Quality Rubric Judge Prompts", ""]
    parts.append("## Label Set Prompt")
    parts.append(build_label_set_prompt(cluster_data))
    for cluster_id, data in cluster_data.items():
        parts.append("")
        parts.append(f"## Cluster Prompt: {cluster_id}")
        parts.append(build_cluster_prompt(cluster_id, data))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(parts), encoding="utf-8")
    print(f"📄 ルーブリック評価プロンプトを保存しました: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="クラスタラベル品質のルーブリック評価（LLM使用）")
    parser.add_argument("--dataset", help="例: example。--dataset-path 未指定時は inputs/{dataset} を読む")
    parser.add_argument(
        "--dataset-path",
        type=Path,
        help="過去出力ディレクトリを直接指定する。hierarchical_merge_labels.csv と hierarchical_clusters.csv が必要",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="評価結果の保存先。省略時は --dataset-path 指定ならそのディレクトリ、未指定なら inputs/{dataset}",
    )
    parser.add_argument("--level", type=int, default=1)
    parser.add_argument("--max-samples", type=int, default=1000)
    parser.add_argument("--sample-mode", choices=["all", "head", "proportional"], default="proportional")
    parser.add_argument("--mode", choices=["api", "print"], default="api")
    parser.add_argument("--model", default="gpt-4o-mini")
    parser.add_argument("--provider", default="openai")
    parser.add_argument("--local-llm-address")
    args = parser.parse_args()

    if args.dataset_path is None and not args.dataset:
        parser.error("--dataset or --dataset-path is required")

    dataset_path = args.dataset_path if args.dataset_path is not None else Path("inputs") / args.dataset
    output_dir = args.output_dir if args.output_dir is not None else dataset_path
    prompt_output_dir = args.output_dir if args.output_dir is not None else Path("outputs") / (args.dataset or dataset_path.name)
    cluster_data = load_cluster_data(dataset_path, args.level, args.max_samples, args.sample_mode)

    if args.mode == "print":
        save_prompts(cluster_data, prompt_output_dir / f"label_rubric_prompt_level{args.level}.txt")
        return

    cluster_results: dict[str, dict[str, Any]] = {}
    token_input = 0
    token_output = 0
    token_total = 0

    label_set_result, in_tokens, out_tokens, total_tokens = evaluate_label_set(
        cluster_data,
        model=args.model,
        provider=args.provider,
        local_llm_address=args.local_llm_address,
    )
    token_input += in_tokens
    token_output += out_tokens
    token_total += total_tokens

    for cluster_id, data in cluster_data.items():
        print(f"Evaluating label rubric: level={args.level} cluster={cluster_id}")
        result, in_tokens, out_tokens, total_tokens = evaluate_cluster(
            cluster_id,
            data,
            model=args.model,
            provider=args.provider,
            local_llm_address=args.local_llm_address,
        )
        cluster_results[cluster_id] = result
        token_input += in_tokens
        token_output += out_tokens
        token_total += total_tokens

    output = {
        "_meta": {
            "rubric_version": RUBRIC_VERSION,
            "level": args.level,
            "model": args.model,
            "provider": args.provider,
            "sample_mode": args.sample_mode,
            "max_samples": args.max_samples,
            "token_usage_input": token_input,
            "token_usage_output": token_output,
            "token_usage_total": token_total,
        },
        "_label_set": label_set_result,
        "_summary": summarize_results(cluster_results, label_set_result),
        **cluster_results,
    }
    save_json(output_dir / f"evaluation_label_rubric_level{args.level}.json", output)


if __name__ == "__main__":
    main()
