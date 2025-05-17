import json
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import TypedDict

import pandas as pd
from pydantic import BaseModel, Field

from services.llm import request_to_chat_ai


class LabellingResult(TypedDict):
    """各クラスタのラベリング結果を表す型"""

    cluster_id: str  # クラスタのID
    label: str  # クラスタのラベル名
    description: str  # クラスタの説明文


def hierarchical_initial_labelling(config: dict) -> None:
    """階層的クラスタリングの初期ラベリングを実行する

    Args:
        config: 設定情報を含む辞書
            - output_dir: 出力ディレクトリ名
            - hierarchical_initial_labelling: 初期ラベリングの設定
                - sampling_num: サンプリング数
                - prompt: LLMへのプロンプト
                - model: 使用するLLMモデル名
                - workers: 並列処理のワーカー数
            - provider: LLMプロバイダー
    """
    dataset = config["output_dir"]
    path = f"outputs/{dataset}/hierarchical_initial_labels.csv"
    clusters_argument_df = pd.read_csv(f"outputs/{dataset}/hierarchical_clusters.csv")

    cluster_id_columns = [col for col in clusters_argument_df.columns if col.startswith("cluster-level-")]
    initial_cluster_id_column = cluster_id_columns[-1]
    sampling_num = config["hierarchical_initial_labelling"]["sampling_num"]
    initial_labelling_prompt = config["hierarchical_initial_labelling"]["prompt"]
    model = config["hierarchical_initial_labelling"]["model"]
    workers = config["hierarchical_initial_labelling"]["workers"]

    initial_label_df = initial_labelling(
        initial_labelling_prompt,
        clusters_argument_df,
        sampling_num,
        model,
        workers,
        config["provider"],
        config.get("local_llm_address"),
    )
    print("start initial labelling")
    initial_clusters_argument_df = clusters_argument_df.merge(
        initial_label_df,
        left_on=initial_cluster_id_column,
        right_on="cluster_id",
        how="left",
    ).rename(
        columns={
            "label": f"{initial_cluster_id_column.replace('-id', '')}-label",
            "description": f"{initial_cluster_id_column.replace('-id', '')}-description",
        }
    )
    print("end initial labelling")
    initial_clusters_argument_df.to_csv(path, index=False)


def initial_labelling(
    prompt: str,
    clusters_df: pd.DataFrame,
    sampling_num: int,
    model: str,
    workers: int,
    provider: str = "openai",
    local_llm_address: str = None,
) -> pd.DataFrame:
    """各クラスタに対して初期ラベリングを実行する

    Args:
        prompt: LLMへのプロンプト
        clusters_df: クラスタリング結果のDataFrame
        sampling_num: 各クラスタからサンプリングする意見の数
        model: 使用するLLMモデル名
        workers: 並列処理のワーカー数

    Returns:
        各クラスタのラベリング結果を含むDataFrame
    """
    cluster_columns = [col for col in clusters_df.columns if col.startswith("cluster-level-")]
    initial_cluster_column = cluster_columns[-1]
    cluster_ids = clusters_df[initial_cluster_column].unique()
    process_func = partial(
        process_initial_labelling,
        df=clusters_df,
        prompt=prompt,
        sampling_num=sampling_num,
        target_column=initial_cluster_column,
        model=model,
        provider=provider,
        local_llm_address=local_llm_address,
    )
    with ThreadPoolExecutor(max_workers=workers) as executor:
        results = list(executor.map(process_func, cluster_ids))
    return pd.DataFrame(results)


class LabellingFromat(BaseModel):
    """ラベリング結果のフォーマットを定義する"""

    label: str = Field(..., description="クラスタのラベル名")
    description: str = Field(..., description="クラスタの説明文")


def process_initial_labelling(
    cluster_id: str,
    df: pd.DataFrame,
    prompt: str,
    sampling_num: int,
    target_column: str,
    model: str,
    provider: str = "openai",
    local_llm_address: str = None,
) -> LabellingResult:
    """個別のクラスタに対してラベリングを実行する

    Args:
        cluster_id: 処理対象のクラスタID
        df: クラスタリング結果のDataFrame
        prompt: LLMへのプロンプト
        sampling_num: サンプリングする意見の数
        target_column: クラスタIDが格納されている列名
        model: 使用するLLMモデル名

    Returns:
        クラスタのラベリング結果
    """
    cluster_data = df[df[target_column] == cluster_id]
    sampling_num = min(sampling_num, len(cluster_data))
    cluster = cluster_data.sample(sampling_num)
    input = "\n".join(cluster["argument"].values)
    messages = [
        {"role": "system", "content": prompt},
        {"role": "user", "content": input},
    ]
    try:
        response = request_to_chat_ai(
            messages=messages,
            model=model,
            provider=provider,
            json_schema=LabellingFromat,
            local_llm_address=local_llm_address,
        )
        response_json = json.loads(response) if isinstance(response, str) else response
        return LabellingResult(
            cluster_id=cluster_id,
            label=response_json.get("label", "エラーでラベル名が取得できませんでした"),
            description=response_json.get("description", "エラーで解説が取得できませんでした"),
        )
    except Exception as e:
        print(e)
        return LabellingResult(
            cluster_id=cluster_id,
            label="エラーでラベル名が取得できませんでした",
            description="エラーで解説が取得できませんでした",
        )
