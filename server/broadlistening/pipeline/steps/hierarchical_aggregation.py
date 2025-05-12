"""Generate a convenient JSON output file."""

import json
from collections import defaultdict
from pathlib import Path
from typing import TypedDict

import pandas as pd

ROOT_DIR = Path(__file__).parent.parent.parent.parent
CONFIG_DIR = ROOT_DIR / "scatter" / "pipeline" / "configs"


class Argument(TypedDict):
    arg_id: str
    argument: str
    comment_id: str
    x: float
    y: float
    p: float
    cluster_ids: list[str]


class Cluster(TypedDict):
    level: int
    id: str
    label: str
    takeaway: str
    value: int
    parent: str
    density_rank_percentile: float | None


def hierarchical_aggregation(config):
    path = f"outputs/{config['output_dir']}/hierarchical_result.json"
    results = {
        "arguments": [],
        "clusters": [],
        "comments": {},
        "propertyMap": {},
        "translations": {},
        "overview": "",
        "config": config,
    }

    arguments = pd.read_csv(f"outputs/{config['output_dir']}/args.csv")
    arguments.set_index("arg-id", inplace=True)
    arg_num = len(arguments)
    relation_df = pd.read_csv(f"outputs/{config['output_dir']}/relations.csv")
    comments = pd.read_csv(f"inputs/{config['input']}.csv")
    clusters = pd.read_csv(f"outputs/{config['output_dir']}/hierarchical_clusters.csv")
    labels = pd.read_csv(f"outputs/{config['output_dir']}/hierarchical_merge_labels.csv")

    hidden_properties_map: dict[str, list[str]] = config["hierarchical_aggregation"]["hidden_properties"]

    results["arguments"] = _build_arguments(clusters)
    results["clusters"] = _build_cluster_value(labels, arg_num)
    # NOTE: 属性に応じたコメントフィルタ機能が実装されておらず、全てのコメントが含まれてしまうので、コメントアウト
    # results["comments"] = _build_comments_value(
    #     comments, arguments, hidden_properties_map
    # )
    results["comment_num"] = len(comments)
    results["translations"] = _build_translations(config)
    # 属性情報のカラムは、元データに対して指定したカラムとclassificationするカテゴリを合わせたもの
    results["propertyMap"] = _build_property_map(arguments, hidden_properties_map, config)

    with open(f"outputs/{config['output_dir']}/hierarchical_overview.txt") as f:
        overview = f.read()
    print("overview")
    print(overview)
    results["overview"] = overview

    with open(path, "w") as file:
        json.dump(results, file, indent=2, ensure_ascii=False)
    # TODO: サンプリングロジックを実装したいが、現状は全件抽出
    create_custom_intro(config)
    if config["is_pubcom"]:
        add_original_comments(labels, arguments, relation_df, clusters, config)


def create_custom_intro(config):
    dataset = config["output_dir"]
    args_path = f"outputs/{dataset}/args.csv"
    comments = pd.read_csv(f"inputs/{config['input']}.csv")
    result_path = f"outputs/{dataset}/hierarchical_result.json"

    input_count = len(comments)
    args_count = len(pd.read_csv(args_path))
    processed_num = min(input_count, config["extraction"]["limit"])

    print(f"Input count: {input_count}")
    print(f"Args count: {args_count}")

    base_custom_intro = """{intro}
分析対象となったデータの件数は{processed_num}件で、これらのデータに対して{provider} APIを用いて{args_count}件の意見（議論）を抽出し、クラスタリングを行った。
"""

    intro = config["intro"]
    provider = config.get("provider", "OpenAI").capitalize()
    custom_intro = base_custom_intro.format(
        intro=intro, processed_num=processed_num, args_count=args_count, provider=provider
    )

    with open(result_path) as f:
        result = json.load(f)
    result["config"]["intro"] = custom_intro
    with open(result_path, "w") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)


def add_original_comments(labels, arguments, relation_df, clusters, config):
    # 大カテゴリ（cluster-level-1）に該当するラベルだけ抽出
    labels_lv1 = labels[labels["level"] == 1][["id", "label"]].rename(
        columns={"id": "cluster-level-1-id", "label": "category_label"}
    )

    # arguments と clusters をマージ（カテゴリ情報付与）
    merged = arguments.merge(clusters[["arg-id", "cluster-level-1-id"]], on="arg-id").merge(
        labels_lv1, on="cluster-level-1-id", how="left"
    )

    # relation_df と結合
    merged = merged.merge(relation_df, on="arg-id", how="left")

    # 元コメント取得
    comments = pd.read_csv(f"inputs/{config['input']}.csv")
    comments["comment-id"] = comments["comment-id"].astype(str)
    merged["comment-id"] = merged["comment-id"].astype(str)

    # 元コメント本文などとマージ
    final_df = merged.merge(comments, on="comment-id", how="left")

    # 必要カラムのみ整形
    final_cols = ["comment-id", "comment-body", "arg-id", "argument", "cluster-level-1-id", "category_label"]
    for col in ["source", "url"]:
        if col in comments.columns:
            final_cols.append(col)

    final_df = final_df[final_cols]
    final_df = final_df.rename(
        columns={
            "cluster-level-1-id": "category_id",
            "category_label": "category",
            "arg-id": "arg_id",
            "argument": "argument",
            "comment-body": "original-comment",
        }
    )

    # 保存
    final_df.to_csv(f"outputs/{config['output_dir']}/final_result_with_comments.csv", index=False)


def _build_arguments(clusters: pd.DataFrame) -> list[Argument]:
    cluster_columns = [col for col in clusters.columns if col.startswith("cluster-level-") and "id" in col]

    arguments: list[Argument] = []
    for _, row in clusters.iterrows():
        cluster_ids = ["0"]
        for cluster_column in cluster_columns:
            cluster_ids.append(row[cluster_column])
        argument: Argument = {
            "arg_id": row["arg-id"],
            "argument": row["argument"],
            "x": row["x"],
            "y": row["y"],
            "p": 0,  # NOTE: 一旦全部0でいれる
            "cluster_ids": cluster_ids,
        }
        arguments.append(argument)
    return arguments


def _build_cluster_value(melted_labels: pd.DataFrame, total_num: int) -> list[Cluster]:
    results: list[Cluster] = [
        Cluster(
            level=0,
            id="0",
            label="全体",
            takeaway="",
            value=total_num,
            parent="",
            density_rank_percentile=0,
        )
    ]

    for _, melted_label in melted_labels.iterrows():
        cluster_value = Cluster(
            level=melted_label["level"],
            id=melted_label["id"],
            label=melted_label["label"],
            takeaway=melted_label["description"],
            value=melted_label["value"],
            parent=melted_label.get("parent", "全体"),
            density_rank_percentile=melted_label.get("density_rank_percentile"),
        )
        results.append(cluster_value)
    return results


def _build_comments_value(
    comments: pd.DataFrame,
    arguments: pd.DataFrame,
    hidden_properties_map: dict[str, list[str]],
):
    comment_dict: dict[str, dict[str, str]] = {}
    useful_comment_ids = set(arguments["comment-id"].values)
    for _, row in comments.iterrows():
        id = row["comment-id"]
        if id in useful_comment_ids:
            res = {"comment": row["comment-body"]}
            should_skip = any(row[prop] in hidden_values for prop, hidden_values in hidden_properties_map.items())
            if should_skip:
                continue
            comment_dict[str(id)] = res

    return comment_dict


def _build_translations(config):
    languages = list(config.get("translation", {}).get("languages", []))
    if len(languages) > 0:
        with open(f"outputs/{config['output_dir']}/translations.json") as f:
            translations = f.read()
        return json.loads(translations)
    return {}


def _build_property_map(
    arguments: pd.DataFrame, hidden_properties_map: dict[str, list[str]], config: dict
) -> dict[str, dict[str, str]]:
    property_columns = list(hidden_properties_map.keys()) + list(config["extraction"]["categories"].keys())
    property_map = defaultdict(dict)

    # 指定された property_columns が arguments に存在するかチェック
    missing_cols = [col for col in property_columns if col not in arguments.columns]
    if missing_cols:
        raise ValueError(
            f"指定されたカラム {missing_cols} が args.csv に存在しません。"
            "設定ファイルaggregation / hidden_propertiesから該当カラムを取り除いてください。"
        )

    for prop in property_columns:
        for arg_id, row in arguments.iterrows():
            # LLMによるcategory classificationがうまく行かず、NaNの場合はNoneにする
            property_map[prop][arg_id] = row[prop] if not pd.isna(row[prop]) else None
    return property_map
