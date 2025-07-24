import json
import os
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from functools import partial

import numpy as np
import pandas as pd
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
    clusters_df = pd.read_csv(f"outputs/{dataset}/hierarchical_initial_labels.csv")

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
    melted_df = melted_df.merge(parent_child_df, on=["level", "id"], how="left")
    density_df = calculate_cluster_density(melted_df, config)
    density_df.to_csv(merge_path, index=False)


def _build_parent_child_mapping(df: pd.DataFrame, cluster_id_columns: list[str]):
    """クラスタ間の親子関係をマッピングする

    Args:
        df: クラスタリング結果のDataFrame
        cluster_id_columns: クラスタIDのカラム名のリスト

    Returns:
        親子関係のマッピング情報を含むDataFrame
    """
    results = []
    top_cluster_column = cluster_id_columns[0]
    top_cluster_values = df[top_cluster_column].unique()
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
        # 現在のレベルのクラスタid
        current_cluster_values = df[current_column].unique()
        for current_id in current_cluster_values:
            children_ids = df.loc[df[current_column] == current_id, children_column].unique()
            for child_id in children_ids:
                results.append(
                    {
                        "level": int(current_level) + 1,
                        "id": child_id,
                        "parent": current_id,
                    }
                )
    return pd.DataFrame(results)


def _filter_id_columns(columns: list[str]) -> list[str]:
    """クラスタIDのカラム名をフィルタリングする

    Args:
        columns: 全カラム名のリスト

    Returns:
        クラスタIDのカラム名のリスト
    """
    return [col for col in columns if col.startswith("cluster-level-") and col.endswith("-id")]


def melt_cluster_data(df: pd.DataFrame) -> pd.DataFrame:
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
        # クラスタidごとの件数集計
        level_count_df = df.groupby(cluster_columns.id).size().reset_index(name="value")

        level_unique_val_df = df[
            [cluster_columns.id, cluster_columns.label, cluster_columns.description]
        ].drop_duplicates()
        level_unique_val_df = level_unique_val_df.merge(level_count_df, on=cluster_columns.id, how="left")
        level_unique_vals = [
            {
                "level": level,
                "id": row[cluster_columns.id],
                "label": row[cluster_columns.label],
                "description": row[cluster_columns.description],
                "value": row["value"],
            }
            for _, row in level_unique_val_df.iterrows()
        ]
        all_rows.extend(level_unique_vals)
    return pd.DataFrame(all_rows)


def merge_labelling(clusters_df: pd.DataFrame, cluster_id_columns: list[str], config) -> pd.DataFrame:
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

        current_cluster_ids = sorted(clusters_df[current_columns.id].unique())
        with ThreadPoolExecutor(max_workers=config["hierarchical_merge_labelling"]["workers"]) as executor:
            responses = list(
                tqdm(
                    executor.map(process_fn, current_cluster_ids),
                    total=len(current_cluster_ids),
                )
            )

        current_result_df = pd.DataFrame(responses)
        clusters_df = clusters_df.merge(current_result_df, on=[current_columns.id])
    return clusters_df


class LabellingFromat(BaseModel):
    """ラベリング結果のフォーマットを定義する"""

    label: str = Field(..., description="クラスタのラベル名")
    description: str = Field(..., description="クラスタの説明文")


def process_merge_labelling(
    target_cluster_id: str,
    result_df: pd.DataFrame,
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

    def filter_previous_values(df: pd.DataFrame, previous_columns: ClusterColumns) -> list[ClusterValues]:
        """前のレベルのクラスタ情報を取得する"""
        previous_records = df[df[current_columns.id] == target_cluster_id][
            [previous_columns.label, previous_columns.description]
        ].drop_duplicates()
        previous_values = [
            ClusterValues(
                label=row[previous_columns.label],
                description=row[previous_columns.description],
            )
            for _, row in previous_records.iterrows()
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

    current_cluster_data = result_df[result_df[current_columns.id] == target_cluster_id]
    sampling_num = min(
        config["hierarchical_merge_labelling"]["sampling_num"],
        len(current_cluster_data),
    )
    sampled_data = current_cluster_data.sample(sampling_num)
    sampled_argument_text = "\n".join(sampled_data["argument"].values)
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


def calculate_cluster_density(melted_df: pd.DataFrame, config: dict):
    """クラスタ内の密度計算"""
    hierarchical_cluster_df = pd.read_csv(f"outputs/{config['output_dir']}/hierarchical_clusters.csv")

    densities = []
    for level, c_id in zip(melted_df["level"], melted_df["id"], strict=False):
        cluster_embeds = hierarchical_cluster_df[hierarchical_cluster_df[f"cluster-level-{level}-id"] == c_id][
            ["x", "y"]
        ].values
        density = calculate_density(cluster_embeds)
        densities.append(density)

    # 密度のランクを計算
    melted_df["density"] = densities
    melted_df["density_rank"] = melted_df.groupby("level")["density"].rank(ascending=False, method="first")
    melted_df["density_rank_percentile"] = melted_df.groupby("level")["density_rank"].transform(lambda x: x / len(x))
    return melted_df


def calculate_density(embeds: np.ndarray):
    """平均距離に基づいて密度を計算"""
    center = np.mean(embeds, axis=0)
    distances = np.linalg.norm(embeds - center, axis=1)
    avg_distance = np.mean(distances)
    density = 1 / (avg_distance + 1e-10)
    return density
