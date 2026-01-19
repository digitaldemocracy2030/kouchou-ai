import json
import math
import sys
from pathlib import Path

import pandas as pd


# -----------------------------
def load_json_with_fallback(path: Path):
    """UTF-8優先 → SJISフォールバックでJSON読み込み"""
    if not path.exists():
        print(f"⚠️ Missing: {path}")
        return {}
    try:
        with open(path, encoding='utf-8') as f:
            return json.load(f)
    except UnicodeDecodeError:
        with open(path, encoding='shift_jis') as f:
            return json.load(f)

# -----------------------------
# 引数でディレクトリ指定（例: python generate_csv.py 2）
# -----------------------------
if len(sys.argv) < 2:
    print("❌ データディレクトリ番号を指定してください（例: python generate_csv.py 2）")
    sys.exit(1)

data_id = sys.argv[1]
data_dir = Path("inputs") / data_id
output_dir = Path("outputs") / data_id

# 入力ファイルパス
LABEL_CSV = data_dir / "hierarchical_merge_labels.csv"
RESULT_JSON = data_dir / "hierarchical_result.json"
EVAL_LLM_JSON_L1 = data_dir / "evaluation_consistency_llm_level1.json"
EVAL_LLM_JSON_L2 = data_dir / "evaluation_consistency_llm_level2.json"
SIL_UMAP_CLUSTER_JSON_L1 = data_dir / "silhouette_umap_level1_clusters.json"
SIL_UMAP_CLUSTER_JSON_L2 = data_dir / "silhouette_umap_level2_clusters.json"
SIL_POINTS_JSON = data_dir / "silhouette_umap_level1_points.json"

# 出力ファイルパス
OUT_CLUSTER_CSV = output_dir / "cluster_evaluation.csv"
OUT_COMMENT_CSV = output_dir / "comment_evaluation.csv"

# -----------------------------
# クラスタ単位の出力
# -----------------------------
def generate_cluster_csv():
    df = pd.read_csv(LABEL_CSV)

    if "cluster_id" not in df.columns:
        if "id" in df.columns:
            df = df.rename(columns={"id": "cluster_id"})
        else:
            raise KeyError("クラスタID列が見つかりません（'cluster_id' または 'id' が必要です）")

    llm_scores_l1 = load_json_with_fallback(EVAL_LLM_JSON_L1)
    llm_scores_l2 = load_json_with_fallback(EVAL_LLM_JSON_L2)
    umap_scores_l1 = load_json_with_fallback(SIL_UMAP_CLUSTER_JSON_L1).get("clusters", {})
    umap_scores_l2 = load_json_with_fallback(SIL_UMAP_CLUSTER_JSON_L2).get("clusters", {})

    llm_scores = {**llm_scores_l1, **llm_scores_l2}
    umap_scores = {**umap_scores_l1, **umap_scores_l2}

    def get_llm_value(cid, key):
        return llm_scores.get(cid, {}).get(key)

    def get_umap_metric(cid, key):
        return umap_scores.get(cid, {}).get(key)

    df["clarity"] = df["cluster_id"].map(lambda x: get_llm_value(x, "clarity"))
    df["coherence"] = df["cluster_id"].map(lambda x: get_llm_value(x, "coherence"))
    df["consistency"] = df["cluster_id"].map(lambda x: get_llm_value(x, "consistency"))
    df["distinctiveness"] = df["cluster_id"].map(lambda x: get_llm_value(x, "distinctiveness"))
    df["llm_comment"] = df["cluster_id"].map(lambda x: get_llm_value(x, "comment"))

    df["silhouette"] = df["cluster_id"].map(lambda x: get_umap_metric(x, "silhouette"))
    df["silhouette_score"] = df["cluster_id"].map(lambda x: get_umap_metric(x, "silhouette_score"))
    df["centroid"] = df["cluster_id"].map(lambda x: get_umap_metric(x, "centroid_dist"))
    df["centroid_score"] = df["cluster_id"].map(lambda x: get_umap_metric(x, "centroid_score"))
    df["nearest"] = df["cluster_id"].map(lambda x: get_umap_metric(x, "nearest_dist"))
    df["nearest_score"] = df["cluster_id"].map(lambda x: get_umap_metric(x, "nearest_score"))

    desired_order = [
        "level", "cluster_id", "label", "description", "value", "parent", "density",
        "density_rank", "density_rank_percentile",
        "clarity", "coherence", "consistency", "distinctiveness", "llm_comment",
        "silhouette", "silhouette_score", "centroid", "centroid_score", "nearest", "nearest_score"
    ]
    df_out = df[[col for col in desired_order if col in df.columns]]
    df_out.to_csv(OUT_CLUSTER_CSV, index=False)

# -----------------------------
# 意見単位の出力
# -----------------------------
def generate_comment_csv():
    result_data = load_json_with_fallback(RESULT_JSON)
    point_scores = load_json_with_fallback(SIL_POINTS_JSON)

    arguments = result_data.get("arguments", [])
    rows = []
    for arg in arguments:
        comment_id = arg["arg_id"]
        argument_text = arg["argument"]
        cluster_ids = arg.get("cluster_ids", [])
        for cluster_id in cluster_ids[1:]:  # 最初のID（全体クラスタ）はスキップ
            p = point_scores.get(comment_id, {})
            row = {
                "comment_id": comment_id,
                "text": argument_text,
                "cluster_id": cluster_id,
                "umap_silhouette": p.get("silhouette"),
                "silhouette": p.get("silhouette"),
                "silhouette_score": p.get("silhouette_score"),
                "centroid": p.get("centroid_dist"),
                "centroid_score": p.get("centroid_score"),
                "nearest": p.get("nearest_dist"),
                "nearest_score": p.get("nearest_score")
            }
            rows.append(row)

    df = pd.DataFrame(rows)
    df.to_csv(OUT_COMMENT_CSV, index=False)

# -----------------------------
if __name__ == "__main__":
    generate_cluster_csv()
    generate_comment_csv()
