"""抽出した意見 1 件ごとに、他の意見からどれだけ離れているか（新規性スコア）を埋め込みから計算する任意ステップ。

LLM は呼ばない。``embeddings.pkl`` を読み、``opinion_novelty.csv`` に 0.0〜1.0 のスコア
（高いほど他の意見から遠い）を書く。``hierarchical_aggregation`` が
``arguments[].attributes.novelty_score`` に数値として入れ、公開ビューアの属性フィルタで
「新規性の高い意見だけ」に絞れる。

「珍しい」と「重要」は別で、スコアは候補を絞るだけ。何を重要と見るかは分析者が決める。
farbrain（tokoroten）の Isolation Forest 方式も ``method`` で選べる。
"""

import json
import os
from typing import Any

import numpy as np
import polars as pl

from analysis_core.core import update_progress
from analysis_core.steps._embeddings_io import load_embeddings_pickle, stack_embedding_rows

NOVELTY_FILENAME = "opinion_novelty.csv"
SUMMARY_FILENAME = "opinion_novelty_summary.json"
SCORE_COLUMN = "novelty_score"
METHOD_KNN = "knn_distance"
METHOD_ISOLATION_FOREST = "isolation_forest"
METHODS = (METHOD_KNN, METHOD_ISOLATION_FOREST)
DEFAULT_K = 10
DEFAULT_SEED = 42
SUMMARY_NOTE = (
    "スコアは埋め込み空間での他の意見からの距離に基づく順位（0.0〜1.0、高いほど他の意見から遠い）で、"
    "人手による検証はしていません。珍しい意見の候補を絞るためのもので、重要さや正しさを表しません。"
    "埋め込みモデルや意見の件数が変わると値も変わります。"
)


def _load_sklearn():
    try:
        from sklearn.ensemble import IsolationForest
        from sklearn.neighbors import NearestNeighbors
    except ImportError as exc:  # pragma: no cover - depends on the installed extras
        raise RuntimeError(
            "opinion_novelty requires the optional 'clustering' dependencies. "
            "Install with: pip install 'kouchou-ai-analysis-core[clustering]'"
        ) from exc
    return NearestNeighbors, IsolationForest


def percentile_rank(values: np.ndarray) -> np.ndarray:
    """値の順位を 0.0〜1.0 に正規化する（同値は平均順位）。1 件なら 0.0。"""
    n = len(values)
    if n < 2:
        return np.zeros(n, dtype=np.float64)
    order = np.argsort(values, kind="stable")
    ranks = np.empty(n, dtype=np.float64)
    ranks[order] = np.arange(n, dtype=np.float64)
    # 同値は平均順位にする（順序の揺れで値が変わらないように）
    sorted_values = values[order]
    start = 0
    while start < n:
        end = start
        while end + 1 < n and sorted_values[end + 1] == sorted_values[start]:
            end += 1
        if end > start:
            ranks[order[start : end + 1]] = (start + end) / 2.0
        start = end + 1
    return ranks / (n - 1)


def knn_mean_distance(embeddings: np.ndarray, k: int) -> np.ndarray:
    """各意見から k 近傍（自分を除く）までの平均コサイン距離。"""
    n = embeddings.shape[0]
    if n < 2:
        return np.zeros(n, dtype=np.float64)
    k = max(1, min(int(k), n - 1))
    NearestNeighbors, _ = _load_sklearn()
    model = NearestNeighbors(n_neighbors=k + 1, metric="cosine", algorithm="brute")
    model.fit(embeddings)
    distances, _ = model.kneighbors(embeddings)
    # 1 列目は自分自身（距離 0）
    return distances[:, 1:].mean(axis=1).astype(np.float64)


def isolation_forest_anomaly(embeddings: np.ndarray, seed: int) -> np.ndarray:
    """Isolation Forest の異常度（大きいほど他から孤立）。"""
    n = embeddings.shape[0]
    if n < 2:
        return np.zeros(n, dtype=np.float64)
    _, IsolationForest = _load_sklearn()
    model = IsolationForest(random_state=int(seed))
    model.fit(embeddings)
    # score_samples は大きいほど正常なので符号を反転する
    return (-model.score_samples(embeddings)).astype(np.float64)


def compute_novelty(embeddings: np.ndarray, method: str = METHOD_KNN, k: int = DEFAULT_K, seed: int = DEFAULT_SEED):
    """新規性スコア（0.0〜1.0 の順位）と、順位化する前の生の値を返す。"""
    if method == METHOD_KNN:
        raw = knn_mean_distance(embeddings, k)
    elif method == METHOD_ISOLATION_FOREST:
        raw = isolation_forest_anomaly(embeddings, seed)
    else:
        raise ValueError(f"opinion_novelty.method は {list(METHODS)} のいずれかにしてください: {method!r}")
    return percentile_rank(raw), raw


def load_aligned_embeddings(path: str, arg_ids: list[str]) -> np.ndarray:
    """``embeddings.pkl`` を args.csv の arg-id 順に並べた float32 行列として読む。"""
    data = load_embeddings_pickle(path)
    if isinstance(data, list):
        if data and "arg-id" in data[0]:
            by_id = {str(item["arg-id"]): item["embedding"] for item in data}
            missing = [arg_id for arg_id in arg_ids if arg_id not in by_id]
            if missing:
                raise ValueError(f"embeddings.pkl に存在しない arg-id があります: {missing[:5]} ...")
            rows = [by_id[arg_id] for arg_id in arg_ids]
        else:
            rows = [item["embedding"] for item in data]
    else:
        rows = data["embedding"].values.tolist()
    matrix = stack_embedding_rows(rows)
    if matrix.shape[0] != len(arg_ids):
        raise ValueError(
            f"args.csv と embeddings.pkl の件数が一致しません: args={len(arg_ids)}, embeddings={matrix.shape[0]}"
        )
    return matrix


def write_novelty(path: str, arg_ids: list[str], scores: np.ndarray) -> pl.DataFrame:
    frame = pl.DataFrame(
        {"arg-id": list(arg_ids), SCORE_COLUMN: [round(float(s), 6) for s in scores]},
        schema={"arg-id": pl.Utf8, SCORE_COLUMN: pl.Float64},
    )
    frame.write_csv(path)
    return frame


def build_summary(raw: np.ndarray, *, method: str, params: dict[str, Any]) -> dict[str, Any]:
    n = int(len(raw))
    return {
        "total": n,
        "method": method,
        "params": params,
        "raw_value": {
            "description": "k 近傍までの平均コサイン距離" if method == METHOD_KNN else "Isolation Forest の異常度",
            "min": float(raw.min()) if n else None,
            "max": float(raw.max()) if n else None,
            "mean": float(raw.mean()) if n else None,
        },
        "note": SUMMARY_NOTE,
    }


def opinion_novelty(config: dict) -> None:
    """Score every row of ``args.csv`` from ``embeddings.pkl`` and write the CSV and summary files.

    Config should contain:
        - output_dir / _output_base_dir: where ``args.csv`` and ``embeddings.pkl`` live
        - opinion_novelty: method (knn_distance | isolation_forest), k, seed
    """
    dataset = config["output_dir"]
    output_base_dir = config.get("_output_base_dir", "outputs")
    step_config = config.get("opinion_novelty", {})
    method = step_config.get("method") or METHOD_KNN
    k = int(step_config.get("k") or DEFAULT_K)
    seed = int(step_config.get("seed") if step_config.get("seed") is not None else DEFAULT_SEED)

    # 失敗したときに前回の結果が集計へ混ざらないよう、先に消しておく
    for filename in (NOVELTY_FILENAME, SUMMARY_FILENAME):
        stale_path = f"{output_base_dir}/{dataset}/{filename}"
        if os.path.exists(stale_path):
            os.remove(stale_path)

    if method not in METHODS:
        raise ValueError(f"opinion_novelty.method は {list(METHODS)} のいずれかにしてください: {method!r}")

    arguments = pl.read_csv(f"{output_base_dir}/{dataset}/args.csv", infer_schema_length=0)
    arg_ids = [str(value) for value in arguments["arg-id"].to_list()]
    update_progress(config, total=1)

    embeddings = load_aligned_embeddings(f"{output_base_dir}/{dataset}/embeddings.pkl", arg_ids)
    scores, raw = compute_novelty(embeddings, method=method, k=k, seed=seed)
    del embeddings

    write_novelty(f"{output_base_dir}/{dataset}/{NOVELTY_FILENAME}", arg_ids, scores)
    params = {"k": k} if method == METHOD_KNN else {"seed": seed}
    summary = build_summary(raw, method=method, params=params)
    with open(f"{output_base_dir}/{dataset}/{SUMMARY_FILENAME}", "w", encoding="utf-8") as file:
        json.dump(summary, file, ensure_ascii=False, indent=2)
    update_progress(config, incr=1)
