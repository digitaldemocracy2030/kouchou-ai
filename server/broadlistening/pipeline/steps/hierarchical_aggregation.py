"""Generate a convenient JSON output file."""

import json
from collections import defaultdict
from pathlib import Path
from typing import Any, TypedDict
import os

import numpy as np
import pandas as pd

ROOT_DIR = Path(__file__).parent.parent.parent.parent
CONFIG_DIR = ROOT_DIR / "scatter" / "pipeline" / "configs"
PIPELINE_DIR = ROOT_DIR / "broadlistening" / "pipeline"


def json_serialize_numpy(obj: Any) -> Any:
    """
    Recursively convert NumPy data types to native Python types for JSON serialization.

    Args:
        obj: Any Python object which might contain NumPy data types

    Returns:
        The same object structure with NumPy types converted to Python native types
    """
    if isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {k: json_serialize_numpy(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [json_serialize_numpy(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(json_serialize_numpy(item) for item in obj)
    else:
        return obj


class Argument(TypedDict):
    arg_id: str
    argument: str
    comment_id: str
    x: float
    y: float
    p: float
    cluster_ids: list[str]
    attributes: dict[str, str] | None
    url: str | None


class Cluster(TypedDict):
    level: int
    id: str
    label: str
    takeaway: str
    value: int
    parent: str
    density_rank_percentile: float | None


def hierarchical_aggregation(config) -> bool:
    try:
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

        results["arguments"] = _build_arguments(clusters, comments, relation_df, config)
        results["clusters"] = _build_cluster_value(labels, arg_num)

        # results["comments"] = _build_comments_value(
        #     comments, arguments, hidden_properties_map
        # )
        results["comment_num"] = len(comments)
        results["translations"] = _build_translations(config)
        # 属性情報のカラムは、元データに対して指定したカラムとclassificationするカテゴリを合わせたもの
        results["propertyMap"] = _build_property_map(arguments, comments, hidden_properties_map, config)

        with open(f"outputs/{config['output_dir']}/hierarchical_overview.txt") as f:
            overview = f.read()
        print("overview")
        print(overview)
        results["overview"] = overview

        # Convert non-serializable NumPy types to native Python types
        results = json_serialize_numpy(results)

        with open(path, "w") as file:
            json.dump(results, file, indent=2, ensure_ascii=False)
        # TODO: サンプリングロジックを実装したいが、現状は全件抽出
        create_custom_intro(config)
        if config["is_pubcom"]:
            add_original_comments(labels, arguments, relation_df, clusters, config)
        return True
    except Exception as e:
        print("error")
        print(e)
        return False


def create_custom_intro(config):
    dataset = config["output_dir"]
    args_path = PIPELINE_DIR / f"outputs/{dataset}/args.csv"
    comments = pd.read_csv(PIPELINE_DIR / f"inputs/{config['input']}.csv")
    result_path = PIPELINE_DIR / f"outputs/{dataset}/hierarchical_result.json"

    input_count = len(comments)
    args_count = len(pd.read_csv(args_path))
    processed_num = min(input_count, config["extraction"]["limit"])

    print(f"Input count: {input_count}")
    print(f"Args count: {args_count}")

    # LLMプロバイダーとモデル名の判定
    def get_llm_provider_display():
        # configからプロバイダー情報を取得（優先）
        provider = config.get("provider", "openai")
        model = config.get("model", "unknown")
        
        # 環境変数による判定（後方互換性）
        use_azure = os.getenv("USE_AZURE", "false").lower() == "true"
        if use_azure and provider == "openai":
            provider = "azure"
        
        # プロバイダー名をマッピング
        provider_names = {
            "openai": "OpenAI API",
            "azure": "Azure OpenAI API", 
            "openrouter": "OpenRouter API",
            "local": "Local LLM"
        }
        
        provider_name = provider_names.get(provider, f"{provider} API")
        return f"{provider_name} ({model})"
    
    llm_provider = get_llm_provider_display()

    base_custom_intro = """{intro}
分析対象となったデータの件数は{processed_num}件で、これらのデータに対して{llm_provider}を用いて{args_count}件の意見（議論）を抽出し、クラスタリングを行った。
"""

    intro = config["intro"]
    custom_intro = base_custom_intro.format(
        intro=intro,
        processed_num=processed_num,
        args_count=args_count,
        llm_provider=llm_provider
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
    comments = pd.read_csv(PIPELINE_DIR / f"inputs/{config['input']}.csv")
    comments["comment-id"] = comments["comment-id"].astype(str)
    merged["comment-id"] = merged["comment-id"].astype(str)

    # 元コメント本文などとマージ
    final_df = merged.merge(comments, on="comment-id", how="left")

    # 必要カラムのみ整形
    final_cols = ["comment-id", "comment-body", "arg-id", "argument", "cluster-level-1-id", "category_label"]

    # 基本カラム
    for col in ["x", "y", "source", "url"]:
        if col in comments.columns:
            final_cols.append(col)

    # 属性カラムを追加
    attribute_columns = []
    for col in comments.columns:
        # attributeプレフィックスが付いたカラムを探す
        if col.startswith("attribute_"):
            attribute_columns.append(col)
            final_cols.append(col)

    print(f"属性カラム検出: {attribute_columns}")

    # 必要なカラムだけ選択
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
    final_df.to_csv(PIPELINE_DIR / f"outputs/{config['output_dir']}/final_result_with_comments.csv", index=False)


def _build_arguments(
    clusters: pd.DataFrame, comments: pd.DataFrame, relation_df: pd.DataFrame, config: dict
) -> list[Argument]:
    """
    Build the arguments list including attribute information from original comments

    Args:
        clusters: DataFrame containing cluster information for each argument
        comments: DataFrame containing original comments with attribute columns
        relation_df: DataFrame relating arguments to original comments
        config: Configuration dictionary containing enable_source_link setting
    """
    cluster_columns = [col for col in clusters.columns if col.startswith("cluster-level-") and "id" in col]

    # Prepare for merging with original comments to get attributes
    comments_copy = comments.copy()
    comments_copy["comment-id"] = comments_copy["comment-id"].astype(str)

    # Get argument to comment mapping
    arg_comment_map = {}
    if "comment-id" in relation_df.columns:
        relation_df["comment-id"] = relation_df["comment-id"].astype(str)
        arg_comment_map = dict(zip(relation_df["arg-id"], relation_df["comment-id"], strict=False))

    # Find attribute columns in comments dataframe
    attribute_columns = [col for col in comments.columns if col.startswith("attribute_")]
    print(f"属性カラム検出: {attribute_columns}")

    arguments: list[Argument] = []
    for _, row in clusters.iterrows():
        cluster_ids = ["0"]
        for cluster_column in cluster_columns:
            cluster_ids.append(str(row[cluster_column]))  # Convert to string to ensure serializable

        # Create base argument
        argument: Argument = {
            "arg_id": str(row["arg-id"]),  # Convert to string to ensure serializable
            "argument": str(row["argument"]),
            "x": float(row["x"]),  # Convert to native float
            "y": float(row["y"]),  # Convert to native float
            "p": 0,  # NOTE: 一旦全部0でいれる
            "cluster_ids": cluster_ids,
            "attributes": None,
            "url": None,
        }

        # Add attributes and URL if available
        if row["arg-id"] in arg_comment_map:
            comment_id = arg_comment_map[row["arg-id"]]
            comment_rows = comments_copy[comments_copy["comment-id"] == comment_id]

            if not comment_rows.empty:
                comment_row = comment_rows.iloc[0]

                # Add URL if available and enabled
                if config.get("enable_source_link", False) and "url" in comment_row and comment_row["url"] is not None:
                    argument["url"] = str(comment_row["url"])

                # Add attributes if available
                if attribute_columns:
                    attributes = {}
                    for attr_col in attribute_columns:
                        # Remove "attribute_" prefix for cleaner attribute names
                        attr_name = attr_col[len("attribute_") :]
                        # Convert potential numpy types to Python native types
                        attr_value = comment_row.get(attr_col, None)
                        if attr_value is not None:
                            if isinstance(attr_value, np.integer):
                                attr_value = int(attr_value)
                            elif isinstance(attr_value, np.floating):
                                attr_value = float(attr_value)
                            elif isinstance(attr_value, np.ndarray):
                                attr_value = attr_value.tolist()
                        attributes[attr_name] = attr_value

                    # Only add non-empty attributes
                    if any(v is not None for v in attributes.values()):
                        argument["attributes"] = attributes

        arguments.append(argument)
    return arguments


def _build_cluster_value(melted_labels: pd.DataFrame, total_num: int) -> list[Cluster]:
    results: list[Cluster] = [
        Cluster(
            level=0,
            id="0",
            label="全体",
            takeaway="",
            value=int(total_num),  # Convert to native int
            parent="",
            density_rank_percentile=0,
        )
    ]

    for _, melted_label in melted_labels.iterrows():
        # Convert potential NumPy types to native Python types
        level = (
            int(melted_label["level"]) if isinstance(melted_label["level"], int | np.integer) else melted_label["level"]
        )
        cluster_id = str(melted_label["id"])
        label = str(melted_label["label"])
        takeaway = str(melted_label["description"])
        value = (
            int(melted_label["value"]) if isinstance(melted_label["value"], int | np.integer) else melted_label["value"]
        )
        parent = str(melted_label.get("parent", "全体"))

        # Handle density_rank_percentile which might be None or a numeric value
        density_rank = melted_label.get("density_rank_percentile")
        if density_rank is not None:
            if isinstance(density_rank, float | np.floating):
                density_rank = float(density_rank)
            elif isinstance(density_rank, int | np.integer):
                density_rank = int(density_rank)

        cluster_value = Cluster(
            level=level,
            id=cluster_id,
            label=label,
            takeaway=takeaway,
            value=value,
            parent=parent,
            density_rank_percentile=density_rank,
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
        with open(PIPELINE_DIR / f"outputs/{config['output_dir']}/translations.json") as f:
            translations = f.read()
        return json.loads(translations)
    return {}


def _build_property_map(
    arguments: pd.DataFrame, comments: pd.DataFrame, hidden_properties_map: dict[str, list[str]], config: dict
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
            value = row[prop] if not pd.isna(row[prop]) else None

            # Convert NumPy types to Python native types
            if value is not None:
                if isinstance(value, np.integer):
                    value = int(value)
                elif isinstance(value, np.floating):
                    value = float(value)
                elif isinstance(value, np.ndarray):
                    value = value.tolist()
                else:
                    # Convert any other types to string to ensure serialization
                    try:
                        value = str(value)
                    except Exception as e:
                        print(f"Error converting value to string: {e}")
                        value = None

            # Make sure arg_id is string
            str_arg_id = str(arg_id)
            property_map[prop][str_arg_id] = value

    return property_map
