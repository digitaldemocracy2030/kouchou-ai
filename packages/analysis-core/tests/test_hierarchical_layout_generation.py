"""Tests for derived layout generation."""

import json
import pickle
from pathlib import Path

from analysis_core.steps.hierarchical_layout_generation import hierarchical_layout_generation


def _result_payload() -> dict:
    return {
        "config": {"name": "layout test", "analysis_mode": "llm_grouping"},
        "overview": "overview",
        "comment_num": 4,
        "arguments": [
            {"arg_id": "a1", "argument": "one", "comment_id": "1", "x": -1.0, "y": -1.0, "p": 0, "cluster_ids": ["0", "c1"], "attributes": None, "url": None},
            {"arg_id": "a2", "argument": "two", "comment_id": "2", "x": -0.5, "y": -0.8, "p": 0, "cluster_ids": ["0", "c1"], "attributes": None, "url": None},
            {"arg_id": "a3", "argument": "three", "comment_id": "3", "x": 1.0, "y": 1.0, "p": 0, "cluster_ids": ["0", "c2"], "attributes": None, "url": None},
            {"arg_id": "a4", "argument": "four", "comment_id": "4", "x": 0.7, "y": 0.8, "p": 0, "cluster_ids": ["0", "c2"], "attributes": None, "url": None},
        ],
        "clusters": [
            {"id": "0", "level": 0, "label": "root", "value": 4, "parent": "", "takeaway": ""},
            {"id": "c1", "level": 1, "label": "cluster 1", "value": 2, "parent": "0", "takeaway": ""},
            {"id": "c2", "level": 1, "label": "cluster 2", "value": 2, "parent": "0", "takeaway": ""},
        ],
    }


def test_generates_embedding_and_semantic_layouts_for_llm_grouping(tmp_path: Path) -> None:
    run_dir = tmp_path / "demo"
    run_dir.mkdir()
    result_path = run_dir / "hierarchical_result.json"
    result_path.write_text(json.dumps(_result_payload(), ensure_ascii=False), encoding="utf-8")

    embeddings = [
        {"arg-id": "a1", "embedding": [-1.0, -0.9, 0.0]},
        {"arg-id": "a2", "embedding": [-0.8, -1.1, 0.1]},
        {"arg-id": "a3", "embedding": [1.0, 1.1, 0.0]},
        {"arg-id": "a4", "embedding": [0.9, 0.8, -0.1]},
    ]
    with open(run_dir / "embeddings.pkl", "wb") as fh:
        pickle.dump(embeddings, fh)

    hierarchical_layout_generation({
        "output_dir": "demo",
        "_output_base_dir": str(tmp_path),
        "layout_generation": {},
    })

    updated = json.loads(result_path.read_text(encoding="utf-8"))
    assert updated["default_layout_id"] == "semantic_island_map"
    assert "embedding_umap" in updated["layouts"]
    assert "semantic_island_map" in updated["layouts"]
    assert updated["layouts"]["embedding_umap"]["points"]["a1"] == {"x": -1.0, "y": -1.0}
    assert set(updated["layouts"]["semantic_island_map"]["points"]) == {"a1", "a2", "a3", "a4"}
    assert set(updated["layouts"]["semantic_island_map"]["clusters"]) == {"c1", "c2"}


def test_preserves_embedding_layout_as_default_when_semantic_disabled(tmp_path: Path) -> None:
    run_dir = tmp_path / "demo"
    run_dir.mkdir()
    result_path = run_dir / "hierarchical_result.json"
    payload = _result_payload()
    payload["config"]["analysis_mode"] = "hierarchical"
    result_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    with open(run_dir / "embeddings.pkl", "wb") as fh:
        pickle.dump([], fh)

    hierarchical_layout_generation({
        "output_dir": "demo",
        "_output_base_dir": str(tmp_path),
        "layout_generation": {"semantic_island_map": {"enabled": False}},
    })

    updated = json.loads(result_path.read_text(encoding="utf-8"))
    assert updated["default_layout_id"] == "embedding_umap"
    assert set(updated["layouts"]) == {"embedding_umap"}
