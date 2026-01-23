import argparse
import json
from pathlib import Path
from typing import Literal

import numpy as np
import pandas as pd
from sklearn.metrics import pairwise_distances, silhouette_samples

# 5段階評価用閾値
UMAP_THRESHOLDS = [-0.25, 0.0, 0.25, 0.50]

def scale_score(value, thresholds):
    if value is None or (isinstance(value, float) and np.isnan(value)):
        return None
    for i, t in enumerate(thresholds):
        if value < t:
            return i + 1
    return len(thresholds) + 1

def clamp_score(val):
    return max(1, min(5, val))

def load_vectors(dataset_path: Path, source: Literal["embedding", "umap"]):
    if source == "embedding":
        df = pd.read_pickle(dataset_path / "embeddings.pkl")
        vectors = np.vstack(df["embedding"].values)
        arg_ids = df["arg-id"].tolist()
    else:
        df = pd.read_csv(dataset_path / "hierarchical_clusters.csv")
        vectors = df[["x", "y"]].values
        arg_ids = df["arg-id"].astype(str).tolist()
    return vectors, arg_ids

def load_cluster_labels(dataset_path: Path, level: int):
    df = pd.read_csv(dataset_path / "hierarchical_clusters.csv")
    col = f"cluster-level-{level}-id"
    df["arg-id"] = df["arg-id"].astype(str)
    return df[["arg-id", col]].rename(columns={col: "cluster_id"})

def duplicate_singleton_vectors(vectors, arg_ids, labels):
    from collections import Counter
    new_vectors, new_ids, new_labels = list(vectors), list(arg_ids), list(labels)
    counter = Counter(labels)
    for lbl in counter:
        if counter[lbl] == 1:
            idx = labels.index(lbl)
            v = vectors[idx]
            perturbation = np.random.normal(scale=1e-6, size=v.shape)
            new_vectors.append(v + perturbation)
            new_ids.append(arg_ids[idx] + "_dup")
            new_labels.append(lbl)
    return np.array(new_vectors), new_ids, new_labels

def compute_centroid_distances(vectors: np.ndarray, labels: np.ndarray):
    centroids = {lbl: vectors[labels == lbl].mean(axis=0) for lbl in np.unique(labels)}
    centroid_dists = np.array([np.linalg.norm(v - centroids[lbl]) for v, lbl in zip(vectors, labels)])
    label_list = list(centroids.keys())
    centroid_array = np.vstack([centroids[l] for l in label_list])
    dist_mat = pairwise_distances(vectors, centroid_array)
    nearest_dists = []
    for i, lbl in enumerate(labels):
        own = label_list.index(lbl)
        nearest_dists.append(np.delete(dist_mat[i], own).min())
    return centroid_dists, np.array(nearest_dists)

def compute_silhouette(dataset_path: Path, level: int, source: Literal["embedding", "umap"]):
    vectors, arg_ids = load_vectors(dataset_path, source)
    labels_df = load_cluster_labels(dataset_path, level)
    label_map = dict(zip(labels_df["arg-id"], labels_df["cluster_id"]))
    labels = [label_map.get(i) for i in arg_ids]
    
    # 💡 補正を適用
    vectors, arg_ids, labels = duplicate_singleton_vectors(vectors, arg_ids, labels)
    
    metrics = pd.DataFrame({"arg-id": arg_ids, "cluster_id": labels})
    metrics["silhouette"] = silhouette_samples(vectors, metrics["cluster_id"].values)
    centroid_dists, nearest_dists = compute_centroid_distances(vectors, metrics["cluster_id"].values)
    metrics["centroid_dist"] = centroid_dists
    metrics["nearest_dist"] = nearest_dists

    # 複製行を除外してクラスタ平均計算
    metrics_clean = metrics[~metrics["arg-id"].str.endswith("_dup")].copy()

    numeric_cols = ["silhouette", "centroid_dist", "nearest_dist"]
    cluster_stats = metrics_clean.groupby("cluster_id")[numeric_cols].mean()

    cd_min, cd_max = cluster_stats["centroid_dist"].min(), cluster_stats["centroid_dist"].max()
    nd_min, nd_max = cluster_stats["nearest_dist"].min(), cluster_stats["nearest_dist"].max()

    cohesion_s = 1 - 2 * ((cluster_stats["centroid_dist"] - cd_min) / (cd_max - cd_min))
    separation_s = 2 * ((cluster_stats["nearest_dist"] - nd_min) / (nd_max - nd_min)) - 1

    cluster_stats["silhouette_score"] = cluster_stats["silhouette"].apply(lambda x: scale_score(x, UMAP_THRESHOLDS))
    cluster_stats["centroid_score"] = cohesion_s.apply(lambda x: scale_score(x, UMAP_THRESHOLDS))
    cluster_stats["nearest_score"] = separation_s.apply(lambda x: scale_score(x, UMAP_THRESHOLDS))

    adj_c, adj_n = [], []
    for cid, row in cluster_stats.iterrows():
        s = int(row["silhouette_score"])
        tgt = s * 2
        c0, n0 = int(row["centroid_score"]), int(row["nearest_score"])
        d = tgt - (c0 + n0)
        if d != 0:
            add_c = (d + (1 if d > 0 else 0)) // 2
            add_n = d - add_c
            c = clamp_score(c0 + add_c)
            n = clamp_score(n0 + add_n)
            if c + n != tgt:
                n = clamp_score(tgt - c)
        else:
            c, n = c0, n0
        adj_c.append(c)
        adj_n.append(n)
    cluster_stats["centroid_score"] = adj_c
    cluster_stats["nearest_score"] = adj_n

    clusters = {
        str(cid): {
            "silhouette": float(row["silhouette"]),
            "silhouette_score": int(row["silhouette_score"]),
            "centroid_dist": float(row["centroid_dist"]),
            "nearest_dist": float(row["nearest_dist"]),
            "centroid_score": int(row["centroid_score"]),
            "nearest_score": int(row["nearest_score"])
        }
        for cid, row in cluster_stats.iterrows()
    }

    overall_avg = {
        "silhouette": float(metrics_clean["silhouette"].mean()),
        "centroid_dist": float(metrics_clean["centroid_dist"].mean()),
        "nearest_dist": float(metrics_clean["nearest_dist"].mean())
    }

    points = {}
    for _, row in metrics.iterrows():
        aid = row["arg-id"]
        sil_s = scale_score(row["silhouette"], UMAP_THRESHOLDS)
        coh_s = 1 - 2 * ((row["centroid_dist"] - cd_min) / (cd_max - cd_min))
        sep_s = 2 * ((row["nearest_dist"] - nd_min) / (nd_max - nd_min)) - 1
        cent_s = scale_score(coh_s, UMAP_THRESHOLDS)
        nei_s = scale_score(sep_s, UMAP_THRESHOLDS)
        tgt = sil_s * 2
        d0 = tgt - (cent_s + nei_s)
        if d0 != 0:
            ac = (d0 + (1 if d0 > 0 else 0)) // 2
            an = d0 - ac
            cent_s = clamp_score(cent_s + ac)
            nei_s = clamp_score(nei_s + an)
            if cent_s + nei_s != tgt:
                nei_s = clamp_score(tgt - cent_s)
        points[aid] = {
            "silhouette": float(row["silhouette"]),
            "silhouette_score": int(sil_s),
            "centroid_dist": float(row["centroid_dist"]),
            "nearest_dist": float(row["nearest_dist"]),
            "centroid_score": int(cent_s),
            "nearest_score": int(nei_s)
        }

    return clusters, overall_avg, points

def save_json(obj, path: str):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)

def main():
    parser = argparse.ArgumentParser(description="クラスタ内部評価 (シルエット & 距離)")
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--level", type=int, default=1)
    parser.add_argument("--source", choices=["embedding", "umap", "both"], default="umap")
    args = parser.parse_args()

    base_path = Path("inputs") / args.dataset
    base_path.mkdir(parents=True, exist_ok=True)
    sources = [args.source] if args.source != "both" else ["embedding", "umap"]

    for src in sources:
        clusters, overall_avg, points = compute_silhouette(base_path, args.level, src)
        if clusters is None:
            continue
        base = base_path / f"silhouette_{src}_level{args.level}"
        save_json({"level": args.level, "source": src, "clusters": clusters, "overall_avg": overall_avg}, str(base) + "_clusters.json")
        save_json(points, str(base) + "_points.json")
        print(f"出力完了: {base}_clusters.json, {base}_points.json")

if __name__ == "__main__":
    main()
