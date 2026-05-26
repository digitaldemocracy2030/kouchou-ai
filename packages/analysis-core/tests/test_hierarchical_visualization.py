"""Tests for the self-contained HTML report visualization step."""

import json
from pathlib import Path

import pytest

from analysis_core.steps.hierarchical_visualization import (
    SOFT_COLORS,
    build_html,
    hierarchical_visualization,
)


def _minimal_payload() -> dict:
    """Smallest viable hierarchical_result.json shape used by the templates."""
    return {
        "config": {"name": "test report", "question": "what?"},
        "overview": "first paragraph.\n\nsecond paragraph.",
        "comment_num": 2,
        "arguments": [
            {
                "arg_id": "A1_0",
                "argument": "alpha",
                "comment_id": "1",
                "x": 0.1,
                "y": 0.2,
                "cluster_ids": ["0", "1_1"],
                "url": None,
            },
            {
                "arg_id": "A2_0",
                "argument": "beta",
                "comment_id": "2",
                "x": -0.3,
                "y": 0.4,
                "cluster_ids": ["0", "1_2"],
                "url": None,
            },
        ],
        "clusters": [
            {"id": "0", "level": 0, "label": "root", "value": 2, "parent": "", "takeaway": ""},
            {"id": "1_1", "level": 1, "label": "alpha cluster", "value": 1, "parent": "0", "takeaway": "talk alpha"},
            {"id": "1_2", "level": 1, "label": "beta cluster", "value": 1, "parent": "0", "takeaway": "talk beta"},
        ],
    }


class TestBuildHtml:
    def test_returns_full_html_document(self) -> None:
        out = build_html(_minimal_payload())
        assert out.startswith("<!DOCTYPE html>")
        assert "</html>" in out
        # The data payload is inlined verbatim
        assert '<script id="report-data" type="application/json">' in out
        # The Plotly bootstrap is included
        assert "Plotly.react" in out

    def test_title_defaults_to_config_name(self) -> None:
        out = build_html(_minimal_payload())
        assert "<title>test report</title>" in out

    def test_explicit_title_overrides_config(self) -> None:
        out = build_html(_minimal_payload(), title="override")
        assert "<title>override</title>" in out

    def test_question_and_overview_rendered(self) -> None:
        out = build_html(_minimal_payload())
        assert "what?" in out
        # Multi-paragraph overview is split on blank lines
        assert "<p>first paragraph.</p>" in out
        assert "<p>second paragraph.</p>" in out

    def test_cluster_labels_appear_in_tree(self) -> None:
        out = build_html(_minimal_payload())
        assert "alpha cluster" in out
        assert "beta cluster" in out
        # Level-1 cluster takeaways are rendered
        assert "talk alpha" in out

    def test_url_pattern_injects_per_argument_url(self) -> None:
        out = build_html(_minimal_payload(), url_pattern="https://example.com/r/{comment_id}")
        # URLs end up on the inlined JSON payload and in the sub-cluster <li> link
        assert '"url":"https://example.com/r/1"' in out
        assert '"url":"https://example.com/r/2"' in out
        # The JS source-link flag is flipped on
        assert "const ENABLE_SOURCE_LINK = true;" in out

    def test_no_url_pattern_disables_source_link(self) -> None:
        out = build_html(_minimal_payload())
        assert "const ENABLE_SOURCE_LINK = false;" in out

    def test_uses_default_layout_catalog_when_present(self) -> None:
        payload = _minimal_payload()
        payload["layouts"] = {
            "embedding_umap": {
                "kind": "point_layout",
                "points": {
                    "A1_0": {"x": 0.1, "y": 0.2},
                    "A2_0": {"x": -0.3, "y": 0.4},
                },
            },
            "semantic_island_map": {
                "kind": "cluster_first",
                "points": {
                    "A1_0": {"x": 9.1, "y": 9.2},
                    "A2_0": {"x": -8.3, "y": -8.4},
                },
            },
        }
        payload["default_layout_id"] = "semantic_island_map"

        out = build_html(payload)

        assert 'const selectedLayoutId = data.default_layout_id || "embedding_umap";' in out
        assert 'const layoutCatalog = data.layouts || {};' in out
        assert '"default_layout_id":"semantic_island_map"' in out
        assert '"A1_0":{"x":9.1,"y":9.2}' in out

    def test_palette_is_inlined(self) -> None:
        out = build_html(_minimal_payload())
        # A representative color from the public-viewer-derived palette
        assert SOFT_COLORS[0] in out

    def test_mst_controls_and_helpers_are_inlined(self) -> None:
        out = build_html(_minimal_payload())
        assert 'id="show-mst" checked' in out
        assert 'id="use-mst-layout" checked' in out
        assert "Show MST skeleton" in out
        assert "Use MST layout" in out
        assert "function buildMstEdges(points)" in out
        assert "function layoutTree(points, mstEdges, options = {})" in out
        assert "function layoutRigidBridgeClusters(clusters, clusterLayouts, initialCenters, bridgeEdges)" in out
        assert "layout=MST" in out
        assert "intra-cluster MST edges" in out

    def test_escapes_script_end_in_payload(self) -> None:
        payload = _minimal_payload()
        payload["overview"] = "first </script> second"
        payload["arguments"][0]["argument"] = "alpha </script> beta"

        out = build_html(payload)

        assert "<\\/script>" in out
        assert "</script> second" not in out


class TestHierarchicalVisualizationStep:
    def test_writes_report_html_next_to_input(self, tmp_path: Path) -> None:
        # Arrange: synthesize the minimum file the step expects.
        output_dir_name = "demo"
        run_dir = tmp_path / output_dir_name
        run_dir.mkdir()
        (run_dir / "hierarchical_result.json").write_text(
            json.dumps(_minimal_payload(), ensure_ascii=False), encoding="utf-8"
        )

        # Act: invoke the step the way the orchestrator does.
        hierarchical_visualization({
            "output_dir": output_dir_name,
            "_output_base_dir": str(tmp_path),
        })

        # Assert: a single-file HTML report appears next to the input.
        report_path = run_dir / "report.html"
        assert report_path.exists()
        html_text = report_path.read_text(encoding="utf-8")
        assert html_text.startswith("<!DOCTYPE html>")
        assert "test report" in html_text

    def test_missing_input_raises(self, tmp_path: Path) -> None:
        with pytest.raises(FileNotFoundError, match="hierarchical_result.json"):
            hierarchical_visualization({
                "output_dir": "no-such-dir",
                "_output_base_dir": str(tmp_path),
            })

    def test_url_pattern_from_config_is_honored(self, tmp_path: Path) -> None:
        output_dir_name = "demo"
        run_dir = tmp_path / output_dir_name
        run_dir.mkdir()
        (run_dir / "hierarchical_result.json").write_text(
            json.dumps(_minimal_payload(), ensure_ascii=False), encoding="utf-8"
        )

        hierarchical_visualization({
            "output_dir": output_dir_name,
            "_output_base_dir": str(tmp_path),
            "report_url_pattern": "https://example.com/r/{comment_id}",
        })

        html_text = (run_dir / "report.html").read_text(encoding="utf-8")
        assert "https://example.com/r/1" in html_text
        assert "const ENABLE_SOURCE_LINK = true;" in html_text
