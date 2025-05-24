import json
import time
from datetime import datetime
from importlib import import_module

import numpy as np
import pandas as pd
import scipy.cluster.hierarchy as sch
from hierarchical_utils import update_status  # ← 追加
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score


def hierarchical_clustering(config):
    UMAP = import_module("umap").UMAP

    dataset = config["output_dir"]
    path = f"outputs/{dataset}/hierarchical_clusters.csv"
    arguments_df = pd.read_csv(f"outputs/{dataset}/args.csv", usecols=["arg-id", "argument"])
    embeddings_df = pd.read_pickle(f"outputs/{dataset}/embeddings.pkl")
    embeddings_array = np.asarray(embeddings_df["embedding"].values.tolist())

    n_samples = embeddings_array.shape[0]
    default_n_neighbors = 15
    # テスト等サンプルが少なすぎる場合、n_neighborsの設定値を下げる
    if n_samples <= default_n_neighbors:
        n_neighbors = max(2, n_samples - 1)
    else:
        n_neighbors = default_n_neighbors

    umap_model = UMAP(random_state=42, n_components=2, n_neighbors=n_neighbors)
    # TODO 詳細エラーメッセージを加える
    # 以下のエラーの場合、おそらく元の意見件数が少なすぎることが原因
    # TypeError: Cannot use scipy.linalg.eigh for sparse A with k >= N. Use scipy.linalg.eigh(A.toarray()) or reduce k.

    umap_embeds = umap_model.fit_transform(embeddings_array)

    # ✅ 自動クラスタ設定の場合
    if config.get("auto_cluster_enabled", False):
        start_time = time.time()

        top_min = config.get("cluster_top_min", 2)
        top_max = config.get("cluster_top_max", 10)
        bottom_max = config.get("cluster_bottom_max", 20)

        n_samples = umap_embeds.shape[0]
        max_clusters = max(2, n_samples - 1)

        # 上下限補正
        top_max = min(top_max, max_clusters)
        bottom_max = min(bottom_max, max_clusters)
        top_min = max(2, min(top_min, top_max))

        silhouette_results = []
        best_top_score, best_top = -1.0, None
        best_bottom_score, best_bottom = -1.0, None

        for k in range(top_min, top_max + 1):
            try:
                labels = KMeans(n_clusters=k, random_state=42).fit_predict(umap_embeds)
                score = silhouette_score(umap_embeds, labels)
                silhouette_results.append((f"top-{k}", float(score)))
                if score > best_top_score:
                    best_top_score, best_top = float(score), int(k)
            except ValueError as e:
                print(f"[auto-cluster] silhouette_score error for top-{k}: {e}")

        for k in range(top_max + 1, bottom_max + 1):
            try:
                labels = KMeans(n_clusters=k, random_state=42).fit_predict(umap_embeds)
                score = silhouette_score(umap_embeds, labels)
                silhouette_results.append((f"bottom-{k}", float(score)))
                if score > best_bottom_score:
                    best_bottom_score, best_bottom = float(score), int(k)
            except ValueError as e:
                print(f"[auto-cluster] silhouette_score error for bottom-{k}: {e}")

        # JSON出力（型変換含む）
        auto_result = {
            "timestamp": datetime.now().isoformat(),
            "top_range": [int(top_min), int(top_max)],
            "bottom_range": [int(top_max + 1), int(bottom_max)],
            "best": {
                "top": {
                    "k": int(best_top) if best_top is not None else None,
                    "score": float(best_top_score) if best_top_score >= 0 else None,
                },
                "bottom": {
                    "k": int(best_bottom) if best_bottom is not None else None,
                    "score": float(best_bottom_score) if best_bottom_score >= 0 else None,
                },
            },
            "duration_sec": round(float(time.time() - start_time), 3),
            "results": [{"label": str(label), "score": float(score)} for label, score in silhouette_results],
        }

        with open(f"outputs/{dataset}/auto_cluster_result.json", "w", encoding="utf-8") as f:
            json.dump(auto_result, f, indent=2, ensure_ascii=False)

        update_status(config, {"auto_cluster_result": auto_result})
        cluster_nums = [best_top, best_bottom]

    else:
        # 通常モード
        cluster_nums = config["hierarchical_clustering"]["cluster_nums"]

    cluster_results = hierarchical_clustering_embeddings(
        umap_embeds=umap_embeds,
        cluster_nums=cluster_nums,
    )

    result_df = pd.DataFrame(
        {
            "arg-id": arguments_df["arg-id"],
            "argument": arguments_df["argument"],
            "x": umap_embeds[:, 0],
            "y": umap_embeds[:, 1],
        }
    )
    for cluster_level, final_labels in enumerate(cluster_results.values(), start=1):
        result_df[f"cluster-level-{cluster_level}-id"] = [f"{cluster_level}_{label}" for label in final_labels]

    result_df.to_csv(path, index=False)


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
