"""Cluster the arguments using UMAP + HDBSCAN and GPT-4."""

import pickle
from importlib import import_module
from pathlib import Path

import numpy as np
import polars as pl
import scipy.cluster.hierarchy as sch
from sklearn.cluster import KMeans

PIPELINE_DIR = Path(__file__).parent.parent


def hierarchical_clustering(config):
    UMAP = import_module("umap").UMAP

    dataset = config["output_dir"]
    path = PIPELINE_DIR / f"outputs/{dataset}/hierarchical_clusters.csv"
    arguments_df = pl.read_csv(PIPELINE_DIR / f"outputs/{dataset}/args.csv", columns=["arg-id", "argument"])

    # embeddings.pkl を読み込み（list[dict] 形式）
    with open(PIPELINE_DIR / f"outputs/{dataset}/embeddings.pkl", "rb") as f:
        embeddings_data = pickle.load(f)

    # list[dict] 形式の場合の処理
    if isinstance(embeddings_data, list) and len(embeddings_data) > 0 and isinstance(embeddings_data[0], dict):
        embeddings_dict = {item["arg-id"]: item["embedding"] for item in embeddings_data}
        # args.csv の順序に合わせて embeddings を取得
        arg_ids = arguments_df["arg-id"].to_list()
        embeddings_list = [embeddings_dict[arg_id] for arg_id in arg_ids]
        embeddings_array = np.asarray(embeddings_list)
    else:
        # 旧形式（pandas DataFrame pickle）の互換性対応
        # pandas DataFrame は直接イテレートするとカラム名が返されるため、
        # ["embedding"] カラムから値を取得する
        embeddings_array = np.asarray(embeddings_data["embedding"].values.tolist())

    cluster_nums = config["hierarchical_clustering"]["cluster_nums"]
    enable_reproducibility = config["hierarchical_clustering"].get("enable_reproducibility", False)

    n_samples = embeddings_array.shape[0]
    # デフォルト設定は15
    default_n_neighbors = 15

    # テスト等サンプルが少なすぎる場合、n_neighborsの設定値を下げる
    if n_samples <= default_n_neighbors:
        n_neighbors = max(2, n_samples - 1)  # 最低2以上
    else:
        n_neighbors = default_n_neighbors

    random_state = 42 if enable_reproducibility else None
    umap_model = UMAP(random_state=random_state, n_components=2, n_neighbors=n_neighbors)
    # TODO 詳細エラーメッセージを加える
    # 以下のエラーの場合、おそらく元の意見件数が少なすぎることが原因
    # TypeError: Cannot use scipy.linalg.eigh for sparse A with k >= N. Use scipy.linalg.eigh(A.toarray()) or reduce k.
    umap_embeds = umap_model.fit_transform(embeddings_array)

    cluster_results = hierarchical_clustering_embeddings(
        umap_embeds=umap_embeds,
        cluster_nums=cluster_nums,
    )
    result_df = pl.DataFrame(
        {
            "arg-id": arguments_df["arg-id"].to_list(),
            "argument": arguments_df["argument"].to_list(),
            "x": umap_embeds[:, 0].tolist(),
            "y": umap_embeds[:, 1].tolist(),
        }
    )

    for cluster_level, final_labels in enumerate(cluster_results.values(), start=1):
        result_df = result_df.with_columns(
            pl.Series(
                name=f"cluster-level-{cluster_level}-id", values=[f"{cluster_level}_{label}" for label in final_labels]
            )
        )

    result_df.write_csv(path)


def generate_cluster_count_list(min_clusters: int, max_clusters: int):
    cluster_counts = []
    current = min_clusters
    cluster_counts.append(current)

    if min_clusters == max_clusters:
        return cluster_counts

    while True:
        next_double = current * 2
        next_triple = current * 3

        if next_double >= max_clusters:
            if cluster_counts[-1] != max_clusters:
                cluster_counts.append(max_clusters)
            break

        # 次の倍はまだ max_clusters に収まるが、3倍だと超える
        # -> (次の倍は細かすぎるので)スキップして max_clusters に飛ぶ
        if next_triple > max_clusters:
            cluster_counts.append(max_clusters)
            break

        cluster_counts.append(next_double)
        current = next_double

    return cluster_counts


def merge_clusters_with_hierarchy(
    cluster_centers: np.ndarray,
    kmeans_labels: np.ndarray,
    umap_array: np.ndarray,
    n_cluster_cut: int,
):
    Z = sch.linkage(cluster_centers, method="ward")
    cluster_labels_merged = sch.fcluster(Z, t=n_cluster_cut, criterion="maxclust")

    n_samples = umap_array.shape[0]
    final_labels = np.zeros(n_samples, dtype=int)

    for i in range(n_samples):
        original_label = kmeans_labels[i]
        final_labels[i] = cluster_labels_merged[original_label]

    return final_labels


def hierarchical_clustering_embeddings(
    umap_embeds,
    cluster_nums,
):
    # 最大分割数でクラスタリングを実施
    print("start initial clustering")
    initial_cluster_num = cluster_nums[-1]
    kmeans_model = KMeans(n_clusters=initial_cluster_num, random_state=42)
    kmeans_model.fit(umap_embeds)
    print("end initial clustering")

    results = {}
    print("start hierarchical clustering")
    cluster_nums.sort()
    print(cluster_nums)
    for n_cluster_cut in cluster_nums[:-1]:
        print("n_cluster_cut: ", n_cluster_cut)
        final_labels = merge_clusters_with_hierarchy(
            cluster_centers=kmeans_model.cluster_centers_,
            kmeans_labels=kmeans_model.labels_,
            umap_array=umap_embeds,
            n_cluster_cut=n_cluster_cut,
        )
        results[n_cluster_cut] = final_labels

    results[initial_cluster_num] = kmeans_model.labels_
    print("end hierarchical clustering")

    return results
