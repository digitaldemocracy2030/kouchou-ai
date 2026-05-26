"""Generate derived 2D layouts for ``hierarchical_result.json``.

This step keeps the canonical argument-level ``x``/``y`` coordinates intact and
adds optional named layouts under ``result["layouts"]``. The immediate use case
is a cluster-first ``semantic_island_map`` for ``llm_grouping`` outputs, while
still preserving the original embedding-derived scatter as ``embedding_umap``.
"""

from __future__ import annotations

import json
import math
import pickle
from pathlib import Path
from typing import Any

def hierarchical_layout_generation(config: dict[str, Any]) -> None:
    """Augment ``hierarchical_result.json`` with derived named layouts."""
    output_dir = config["output_dir"]
    output_base_dir = config.get("_output_base_dir", "outputs")
    result_path = Path(output_base_dir) / output_dir / "hierarchical_result.json"
    embeddings_path = Path(output_base_dir) / output_dir / "embeddings.pkl"

    if not result_path.exists():
        raise FileNotFoundError(
            f"hierarchical_result.json not found at {result_path}. "
            "Run the hierarchical_aggregation step first."
        )

    result = json.loads(result_path.read_text(encoding="utf-8"))
    layouts = dict(result.get("layouts") or {})
    layouts["embedding_umap"] = _build_embedding_layout(result)

    layout_config = config.get("layout_generation", {})
    semantic_cfg = layout_config.get("semantic_island_map", {})
    enabled = semantic_cfg.get("enabled")
    if enabled is None:
        enabled = _should_enable_semantic_layout(result)

    if enabled:
        if not embeddings_path.exists():
            raise FileNotFoundError(
                f"embeddings.pkl not found at {embeddings_path}. "
                "semantic_island_map requires embedding outputs."
            )
        layouts["semantic_island_map"] = _build_semantic_island_layout(
            result=result,
            embeddings_path=embeddings_path,
            center_scale=float(semantic_cfg.get("center_scale", 8.5)),
            island_shrink=float(semantic_cfg.get("island_shrink", 0.72)),
        )

    result["layouts"] = layouts
    result["default_layout_id"] = _resolve_default_layout_id(result, layout_config, enabled)
    result_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")


def _should_enable_semantic_layout(result: dict[str, Any]) -> bool:
    config = result.get("config") or {}
    return config.get("analysis_mode") == "llm_grouping"


def _resolve_default_layout_id(
    result: dict[str, Any],
    layout_config: dict[str, Any],
    semantic_enabled: bool,
) -> str:
    explicit = layout_config.get("default_layout")
    if isinstance(explicit, str) and explicit:
        return explicit
    existing = result.get("default_layout_id")
    if isinstance(existing, str) and existing:
        return existing
    if semantic_enabled:
        return "semantic_island_map"
    return "embedding_umap"


def _build_embedding_layout(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": "point_layout",
        "points": {
            arg["arg_id"]: {"x": float(arg["x"]), "y": float(arg["y"])}
            for arg in result.get("arguments", [])
        },
        "meta": {
            "source": "arguments.xy",
        },
    }


def _build_semantic_island_layout(
    *,
    result: dict[str, Any],
    embeddings_path: Path,
    center_scale: float,
    island_shrink: float,
) -> dict[str, Any]:
    import numpy as np
    from sklearn.metrics.pairwise import cosine_distances

    args = result["arguments"]
    arg_ids = [arg["arg_id"] for arg in args]
    embeddings = _load_embeddings(embeddings_path, arg_ids)

    cluster_ids = [arg["cluster_ids"][-1] for arg in args]
    unique_clusters = list(dict.fromkeys(cluster_ids))
    cluster_indices = {cid: [i for i, value in enumerate(cluster_ids) if value == cid] for cid in unique_clusters}

    centroids = np.vstack([embeddings[cluster_indices[cid]].mean(axis=0) for cid in unique_clusters])
    distance_matrix = cosine_distances(centroids)
    center_coords = _classical_mds(distance_matrix, scale=center_scale)

    radii = {
        cid: island_shrink * (1.3 + math.sqrt(len(cluster_indices[cid])) * 0.26)
        for cid in unique_clusters
    }
    centers = {cid: center_coords[i].copy() for i, cid in enumerate(unique_clusters)}
    _resolve_center_overlaps(centers, radii)

    point_layout: dict[str, dict[str, float]] = {}
    cluster_layout: dict[str, dict[str, float]] = {}
    for cid in unique_clusters:
        idx = cluster_indices[cid]
        local_coords = _local_island_points(embeddings[idx], len(idx), shrink=island_shrink)
        center = centers[cid]
        cluster_layout[cid] = {
            "cx": float(center[0]),
            "cy": float(center[1]),
            "radius": float(radii[cid]),
            "count": len(idx),
        }
        for local_idx, arg_idx in enumerate(idx):
            point_layout[arg_ids[arg_idx]] = {
                "x": float(center[0] + local_coords[local_idx, 0]),
                "y": float(center[1] + local_coords[local_idx, 1]),
            }

    return {
        "kind": "cluster_first",
        "points": point_layout,
        "clusters": cluster_layout,
        "meta": {
            "cluster_layout": "centroid_mds",
            "intra_cluster_layout": "local_pca_radialized",
            "center_scale": center_scale,
            "island_shrink": island_shrink,
        },
    }


def _load_embeddings(embeddings_path: Path, arg_ids: list[str]) -> np.ndarray:
    import numpy as np

    embeddings_data = pickle.loads(embeddings_path.read_bytes())
    if isinstance(embeddings_data, list):
        embedding_by_id = {item["arg-id"]: item["embedding"] for item in embeddings_data}
        return np.asarray([embedding_by_id[arg_id] for arg_id in arg_ids], dtype=np.float64)

    return np.asarray(embeddings_data["embedding"].values.tolist(), dtype=np.float64)


def _classical_mds(distance_matrix: np.ndarray, scale: float = 1.0) -> np.ndarray:
    import numpy as np

    n = distance_matrix.shape[0]
    centering = np.eye(n) - np.ones((n, n)) / n
    gram = -0.5 * centering @ (distance_matrix**2) @ centering
    eigenvalues, eigenvectors = np.linalg.eigh(gram)
    order = np.argsort(eigenvalues)[::-1]
    eigenvalues = np.maximum(eigenvalues[order][:2], 0)
    eigenvectors = eigenvectors[:, order][:, :2]
    coords = eigenvectors * np.sqrt(eigenvalues)
    return coords * scale


def _resolve_center_overlaps(centers: dict[str, np.ndarray], radii: dict[str, float], steps: int = 180) -> None:
    import numpy as np

    cluster_ids = list(centers.keys())
    original = {cid: centers[cid].copy() for cid in cluster_ids}

    for _ in range(steps):
        forces = {cid: np.zeros(2, dtype=np.float64) for cid in cluster_ids}
        for i, left_id in enumerate(cluster_ids):
            for right_id in cluster_ids[i + 1 :]:
                delta = centers[right_id] - centers[left_id]
                dist = np.linalg.norm(delta) or 1e-6
                direction = delta / dist
                min_gap = radii[left_id] + radii[right_id] + 0.6
                if dist < min_gap:
                    push = (min_gap - dist) * 0.18
                    forces[left_id] -= direction * push
                    forces[right_id] += direction * push
        for cid in cluster_ids:
            forces[cid] += (original[cid] - centers[cid]) * 0.01
            centers[cid] += np.clip(forces[cid], -0.25, 0.25)


def _local_island_points(embeddings: np.ndarray, n_points: int, shrink: float) -> np.ndarray:
    import numpy as np
    from sklearn.decomposition import PCA

    if n_points == 1:
        return np.zeros((1, 2), dtype=np.float64)

    centered = embeddings - embeddings.mean(axis=0, keepdims=True)
    local2 = PCA(n_components=2, random_state=42).fit_transform(centered)
    local_norm = np.linalg.norm(local2, axis=1)
    angle = np.arctan2(local2[:, 1], local2[:, 0])
    order = np.argsort(local_norm)
    rank = np.empty_like(order)
    rank[order] = np.arange(n_points)

    max_rank = max(1, n_points - 1)
    max_radius = shrink * (1.1 + math.sqrt(n_points) * 0.22)
    radius = max_radius * np.sqrt(rank / max_rank)

    coords = np.zeros((n_points, 2), dtype=np.float64)
    coords[:, 0] = np.cos(angle) * radius
    coords[:, 1] = np.sin(angle) * radius

    if np.std(angle) < 0.15:
        golden = math.pi * (3 - math.sqrt(5))
        for idx in range(n_points):
            r = max_radius * math.sqrt(idx / max_rank)
            theta = idx * golden
            coords[idx, 0] = math.cos(theta) * r
            coords[idx, 1] = math.sin(theta) * r

    return coords
