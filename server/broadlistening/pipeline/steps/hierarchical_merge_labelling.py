import json
import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from functools import partial

import numpy as np
import polars as pl
from pydantic import BaseModel, Field
from tqdm import tqdm

from services.llm import request_to_chat_ai


@dataclass
class ClusterColumns:
    """同一階層のクラスター関連のカラム名を管理するクラス"""

    id: str
    label: str
    description: str

    @classmethod
    def from_id_column(cls, id_column: str) -> "ClusterColumns":
        """ID列名から関連するカラム名を生成"""
        return cls(
            id=id_column,
            label=id_column.replace("-id", "-label"),
            description=id_column.replace("-id", "-description"),
        )


@dataclass
class ClusterValues:
    """対象クラスタのlabel/descriptionを管理するクラス"""

    label: str
    description: str

    def to_prompt_text(self) -> str:
        return f"- {self.label}: {self.description}"


def hierarchical_merge_labelling(config: dict) -> None:
    """階層的クラスタリングの結果に対してマージラベリングを実行する

    Args:
        config: 設定情報を含む辞書
            - output_dir: 出力ディレクトリ名
            - hierarchical_merge_labelling: マージラベリングの設定
                - sampling_num: サンプリング数
                - prompt: LLMへのプロンプト
                - model: 使用するLLMモデル名
                - workers: 並列処理のワーカー数
            - provider: LLMプロバイダー
    """
    dataset = config["output_dir"]
    merge_path = f"outputs/{dataset}/hierarchical_merge_labels.csv"
    clusters_df = pl.read_csv(f"outputs/{dataset}/hierarchical_initial_labels.csv")

    cluster_id_columns: list[str] = _filter_id_columns(clusters_df.columns)
    # ボトムクラスタのラベル・説明とクラスタid付きの各argumentを入力し、各階層のクラスタラベル・説明を生成し、argumentに付けたdfを作成
    merge_result_df = merge_labelling(
        clusters_df=clusters_df,
        cluster_id_columns=sorted(cluster_id_columns, reverse=True),
        config=config,
    )
    # 上記のdfから各クラスタのlevel, id, label, description, valueを取得してdfを作成
    melted_df = melt_cluster_data(merge_result_df)
    # 上記のdfに親子関係を追加
    parent_child_df = _build_parent_child_mapping(merge_result_df, cluster_id_columns)
    melted_df = melted_df.join(parent_child_df, on=["level", "id"], how="left")
    density_df = calculate_cluster_density(melted_df, config)
    density_df.write_csv(merge_path)


def _build_parent_child_mapping(df: pl.DataFrame, cluster_id_columns: list[str]) -> pl.DataFrame:
    """クラスタ間の親子関係をマッピングする

    Args:
        df: クラスタリング結果のDataFrame
        cluster_id_columns: クラスタIDのカラム名のリスト

    Returns:
        親子関係のマッピング情報を含むDataFrame
    """
    results = []
    top_cluster_column = cluster_id_columns[0]
    top_cluster_values = df.select(top_cluster_column).unique().to_series().to_list()
    for c in top_cluster_values:
        results.append(
            {
                "level": 1,
                "id": c,
                "parent": "0",  # aggregationで追加する全体クラスタのid
            }
        )

    for idx in range(len(cluster_id_columns) - 1):
        current_column = cluster_id_columns[idx]
        children_column = cluster_id_columns[idx + 1]
        current_level = current_column.replace("-id", "").replace("cluster-level-", "")
        current_cluster_values = df.select(current_column).unique().to_series().to_list()
        for current_id in current_cluster_values:
            children_ids = (
                df.filter(pl.col(current_column) == current_id).select(children_column).unique().to_series().to_list()
            )
            for child_id in children_ids:
                results.append(
                    {
                        "level": int(current_level) + 1,
                        "id": child_id,
                        "parent": current_id,
                    }
                )
    if not results:
        return pl.DataFrame({"level": [], "id": [], "parent": []})
    return pl.DataFrame(results)


def _filter_id_columns(columns: list[str]) -> list[str]:
    """クラスタIDのカラム名をフィルタリングする

    Args:
        columns: 全カラム名のリスト

    Returns:
        クラスタIDのカラム名のリスト
    """
    return [col for col in columns if col.startswith("cluster-level-") and col.endswith("-id")]


def melt_cluster_data(df: pl.DataFrame) -> pl.DataFrame:
    """クラスタデータを行形式に変換する

    cluster-level-n-(id|label|description) を行形式 (level, id, label, description, value) にまとめる。
    [cluster-level-n-id, cluster-level-n-label, cluster-level-n-description] を [level, id, label, description, value(件数)] に変換する。

    Args:
        df: クラスタリング結果のDataFrame

    Returns:
        行形式に変換されたDataFrame
    """
    id_columns: list[str] = _filter_id_columns(df.columns)
    levels: set[int] = {int(col.replace("cluster-level-", "").replace("-id", "")) for col in id_columns}
    all_rows: list[dict] = []

    # levelごとに各クラスタの出現件数を集計・縦持ちにする
    for level in levels:
        cluster_columns = ClusterColumns.from_id_column(f"cluster-level-{level}-id")
        level_count_df = df.group_by(cluster_columns.id).len().rename({"len": "value"})
        level_unique_val_df = (
            df.select([cluster_columns.id, cluster_columns.label, cluster_columns.description])
            .unique()
            .join(level_count_df, on=cluster_columns.id, how="left")
        )
        for row in level_unique_val_df.iter_rows(named=True):
            all_rows.append(
                {
                    "level": level,
                    "id": row[cluster_columns.id],
                    "label": row[cluster_columns.label],
                    "description": row[cluster_columns.description],
                    "value": row["value"],
                }
            )
    if not all_rows:
        return pl.DataFrame(
            {
                "level": [],
                "id": [],
                "label": [],
                "description": [],
                "value": [],
            }
        )
    return pl.DataFrame(all_rows)


def merge_labelling(clusters_df: pl.DataFrame, cluster_id_columns: list[str], config) -> pl.DataFrame:
    """階層的なクラスタのマージラベリングを実行する

    Args:
        clusters_df: クラスタリング結果のDataFrame
        cluster_id_columns: クラスタIDのカラム名のリスト
        config: 設定情報を含む辞書

    Returns:
        マージラベリング結果を含むDataFrame
    """
    for idx in tqdm(range(len(cluster_id_columns) - 1)):
        previous_columns = ClusterColumns.from_id_column(cluster_id_columns[idx])
        current_columns = ClusterColumns.from_id_column(cluster_id_columns[idx + 1])

        process_fn = partial(
            process_merge_labelling,
            result_df=clusters_df,
            current_columns=current_columns,
            previous_columns=previous_columns,
            config=config,
        )

        current_cluster_ids = sorted(clusters_df.select(current_columns.id).unique().to_series().to_list())
        with ThreadPoolExecutor(max_workers=config["hierarchical_merge_labelling"]["workers"]) as executor:
            responses = list(
                tqdm(
                    executor.map(process_fn, current_cluster_ids),
                    total=len(current_cluster_ids),
                )
            )

        current_result_df = pl.DataFrame(responses)
        clusters_df = clusters_df.join(current_result_df, on=current_columns.id, how="left")
    return clusters_df


class LabellingFromat(BaseModel):
    """ラベリング結果のフォーマットを定義する"""

    label: str = Field(..., description="クラスタのラベル名")
    description: str = Field(..., description="クラスタの説明文")


def process_merge_labelling(
    target_cluster_id: str,
    result_df: pl.DataFrame,
    current_columns: ClusterColumns,
    previous_columns: ClusterColumns,
    config,
):
    """個別のクラスタに対してマージラベリングを実行する

    Args:
        target_cluster_id: 処理対象のクラスタID
        result_df: クラスタリング結果のDataFrame
        current_columns: 現在のレベルのカラム情報
        previous_columns: 前のレベルのカラム情報
        config: 設定情報を含む辞書

    Returns:
        マージラベリング結果を含む辞書
    """

    def filter_previous_values(df: pl.DataFrame, previous_columns: ClusterColumns) -> list[ClusterValues]:
        """前のレベルのクラスタ情報を取得する"""
        previous_records = (
            df.filter(pl.col(current_columns.id) == target_cluster_id)
            .select([previous_columns.label, previous_columns.description])
            .unique()
        )
        previous_values = [
            ClusterValues(
                label=row[previous_columns.label],
                description=row[previous_columns.description],
            )
            for row in previous_records.iter_rows(named=True)
        ]
        return previous_values

    previous_values = filter_previous_values(result_df, previous_columns)
    if len(previous_values) == 1:
        return {
            current_columns.id: target_cluster_id,
            current_columns.label: previous_values[0].label,
            current_columns.description: previous_values[0].description,
        }
    elif len(previous_values) == 0:
        raise ValueError(f"クラスタ {target_cluster_id} には前のレベルのクラスタが存在しません。")

    current_cluster_data = result_df.filter(pl.col(current_columns.id) == target_cluster_id)
    sampling_num = min(
        config["hierarchical_merge_labelling"]["sampling_num"],
        current_cluster_data.height,
    )
    sampled_data = current_cluster_data.sample(sampling_num) if sampling_num > 0 else current_cluster_data
    sampled_argument_text = "\n".join(sampled_data["argument"].to_list())
    cluster_text = "\n".join([value.to_prompt_text() for value in previous_values])
    messages = [
        {"role": "system", "content": config["hierarchical_merge_labelling"]["prompt"]},
        {
            "role": "user",
            "content": "クラスタラベル\n" + cluster_text + "\n" + "クラスタの意見\n" + sampled_argument_text,
        },
    ]
    try:
        response_text, token_input, token_output, token_total = request_to_chat_ai(
            messages=messages,
            model=config["hierarchical_merge_labelling"]["model"],
            json_schema=LabellingFromat,
            provider=config["provider"],
            local_llm_address=config.get("local_llm_address"),
            user_api_key=os.getenv("USER_API_KEY"),
        )

        config["total_token_usage"] = config.get("total_token_usage", 0) + token_total
        config["token_usage_input"] = config.get("token_usage_input", 0) + token_input
        config["token_usage_output"] = config.get("token_usage_output", 0) + token_output
        print(f"Merge labelling: input={token_input}, output={token_output}, total={token_total} tokens")

        response_json = json.loads(response_text) if isinstance(response_text, str) else response_text
        return {
            current_columns.id: target_cluster_id,
            current_columns.label: response_json.get("label", "エラーでラベル名が取得できませんでした"),
            current_columns.description: response_json.get("description", "エラーで解説が取得できませんでした"),
        }
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        return {
            current_columns.id: target_cluster_id,
            current_columns.label: "エラーでラベル名が取得できませんでした",
            current_columns.description: "エラーで解説が取得できませんでした",
        }


def calculate_cluster_density(melted_df: pl.DataFrame, config: dict):
    """クラスタ内の密度計算"""
    hierarchical_cluster_df = pl.read_csv(f"outputs/{config['output_dir']}/hierarchical_clusters.csv")

    densities = []
    for level, c_id in zip(melted_df["level"].to_list(), melted_df["id"].to_list(), strict=False):
        column_name = f"cluster-level-{level}-id"
        cluster_embeds_df = hierarchical_cluster_df.filter(pl.col(column_name) == c_id).select(["x", "y"])
        embeds_array = cluster_embeds_df.to_numpy()
        density = calculate_density(embeds_array) if embeds_array.size > 0 else 0
        densities.append(density)

    # 密度のランクを計算
    melted_df = melted_df.with_columns(pl.Series("density", densities))
    melted_df = melted_df.with_columns(
        pl.col("density").rank(method="ordinal", descending=True).over("level").alias("density_rank")
    )
    melted_df = melted_df.with_columns(
        (pl.col("density_rank") / pl.len().over("level")).alias("density_rank_percentile")
    )
    return melted_df


def calculate_density(embeds: np.ndarray):
    """平均距離に基づいて密度を計算"""
    center = np.mean(embeds, axis=0)
    distances = np.linalg.norm(embeds - center, axis=1)
    avg_distance = np.mean(distances)
    density = 1 / (avg_distance + 1e-10)
    return density
