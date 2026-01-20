"""Cluster the arguments using UMAP + HDBSCAN and GPT-4."""

import pickle
from importlib import import_module

import numpy as np
import polars as pl
import scipy.cluster.hierarchy as sch
from sklearn.cluster import KMeans


def hierarchical_clustering(config):
    UMAP = import_module("umap").UMAP

    dataset = config["output_dir"]
    path = f"outputs/{dataset}/hierarchical_clusters.csv"
    arguments_df = pl.read_csv(f"outputs/{dataset}/args.csv", columns=["arg-id", "argument"])
    embeddings_path = f"outputs/{dataset}/embeddings.pkl"
    try:
        with open(embeddings_path, "rb") as f:
            embeddings_obj = pickle.load(f)
    except ModuleNotFoundError as exc:
        msg = (
            "旧形式(pandas DataFrame)の embeddings.pkl を読み込めません。"
            "再度 embedding ステップを実行してファイルを再生成してください。"
        )
        raise RuntimeError(msg) from exc
    if not isinstance(embeddings_obj, list):
        raise RuntimeError(f"サポートされていない embeddings.pkl 形式です: {type(embeddings_obj)}")
    embeddings_map: dict[str, list[float]] = {}
    for row in embeddings_obj:
        if not isinstance(row, dict):
            raise RuntimeError(
                "embeddings.pkl の各要素は dict である必要があります。再度 embedding ステップを実行してください。"
            )
        arg_id = row.get("arg-id")
        embedding = row.get("embedding")
        if arg_id is None or embedding is None:
            raise RuntimeError(
                "embeddings.pkl に arg-id または embedding が含まれていません。再度 embedding ステップを実行してください。"
            )
        if arg_id in embeddings_map:
            raise RuntimeError(
                f"embeddings.pkl に重複した arg-id '{arg_id}' が含まれています。再度 embedding ステップを実行してください。"
            )
        embeddings_map[arg_id] = embedding

    arg_ids = arguments_df["arg-id"].to_list()
    missing_embeddings = [arg_id for arg_id in arg_ids if arg_id not in embeddings_map]
    if missing_embeddings:
        raise RuntimeError(
            "embeddings.pkl に不足している arg-id があります。"
            f"不足: {missing_embeddings[:5]}{'...' if len(missing_embeddings) > 5 else ''}"
        )
    extra_embeddings = [arg_id for arg_id in embeddings_map.keys() if arg_id not in arg_ids]
    if extra_embeddings:
        raise RuntimeError(
            "embeddings.pkl に args.csv に存在しない arg-id が含まれています。"
            f"余剰: {extra_embeddings[:5]}{'...' if len(extra_embeddings) > 5 else ''}"
        )

    embeddings_array = np.asarray([embeddings_map[arg_id] for arg_id in arg_ids])
    cluster_nums = config["hierarchical_clustering"]["cluster_nums"]

    n_samples = embeddings_array.shape[0]
    # デフォルト設定は15
    default_n_neighbors = 15

    # テスト等サンプルが少なすぎる場合、n_neighborsの設定値を下げる
    if n_samples <= default_n_neighbors:
        n_neighbors = max(2, n_samples - 1)  # 最低2以上
    else:
        n_neighbors = default_n_neighbors

    umap_model = UMAP(random_state=42, n_components=2, n_neighbors=n_neighbors)
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
            pl.Series(f"cluster-level-{cluster_level}-id", [f"{cluster_level}_{label}" for label in final_labels])
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
