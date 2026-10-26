"""Tests for the self-contained HTML report visualization step."""

import base64
import io
import json
import re
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

from analysis_core.steps.hierarchical_visualization import (
    SOFT_COLORS,
    _render_tree,
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

    @pytest.mark.parametrize(
        "bad_url",
        [
            "javascript:alert(document.domain)",
            "  JavaScript:alert(1)",
            "data:text/html,<script>alert(1)</script>",
            "vbscript:msgbox(1)",
        ],
    )
    def test_non_http_source_urls_are_dropped(self, bad_url: str) -> None:
        payload = _minimal_payload()
        # Add a level-2 layer so the tree renders per-argument source links
        payload["clusters"] += [
            {"id": "2_1", "level": 2, "label": "a2", "value": 1, "parent": "1_1", "takeaway": ""},
            {"id": "2_2", "level": 2, "label": "b2", "value": 1, "parent": "1_2", "takeaway": ""},
        ]
        payload["arguments"][0]["cluster_ids"] = ["0", "1_1", "2_1"]
        payload["arguments"][1]["cluster_ids"] = ["0", "1_2", "2_2"]
        payload["arguments"][0]["url"] = bad_url
        payload["arguments"][1]["url"] = "https://example.com/ok"
        for url_pattern in (None, "https://example.com/r/{comment_id}"):
            out = build_html(payload, url_pattern=url_pattern)
            lowered = out.lower()
            assert "javascript:" not in lowered
            assert "vbscript:" not in lowered
            assert "data:text/html" not in lowered
            # http(s) URLs keep working in the tree link and the inlined payload
            assert 'href="https://example.com/ok"' in out
            assert '"url":"https://example.com/ok"' in out

    def test_url_pattern_fills_in_for_rejected_source_url(self) -> None:
        payload = _minimal_payload()
        payload["arguments"][0]["url"] = "javascript:alert(1)"
        out = build_html(payload, url_pattern="https://example.com/r/{comment_id}")
        assert "javascript:" not in out.lower()
        # The unsafe url is dropped first, so the url_pattern link is used instead
        assert '"url":"https://example.com/r/1"' in out

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

        assert "\\u003c/script\\u003e" in out
        assert "</script> second" not in out

    @pytest.mark.parametrize(
        ("overview", "argument"),
        [
            # 同じ意見の中で「<!--」の後に「<script」が来る
            ("plain overview", "例: <!--<script> のような書き方は避けて"),
            # 概要と意見にまたがる（埋め込み JSON の中で、概要の後に意見が並ぶ）
            ("概要 <!-- メモ", "<script タグについて"),
        ],
    )
    def test_markup_in_payload_does_not_break_embedded_json(self, overview: str, argument: str) -> None:
        payload = _minimal_payload()
        payload["overview"] = overview
        payload["arguments"][0]["argument"] = argument
        payload["arguments"][1]["argument"] = "a & b > c </script>"

        out = build_html(payload)

        match = re.search(r'<script id="report-data" type="application/json">(.*?)</script>', out, flags=re.S)
        assert match is not None
        embedded = match.group(1)
        # HTML の字句解析が script data の状態を変える文字（<）を JSON に残さない
        assert "<" not in embedded
        assert ">" not in embedded
        assert "&" not in embedded
        # JSON としては元の値のまま読める
        decoded = json.loads(embedded)
        assert decoded["overview"] == overview
        assert decoded["arguments"][0]["argument"] == argument
        assert decoded["arguments"][1]["argument"] == "a & b > c </script>"
        # 本体のスクリプトは report-data の後ろに別の要素として残る
        assert out.index("const SOFT_COLORS") > match.end()


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


class TestReportLicense:
    def test_source_bundle_is_data_free_and_renders_without_the_package(self, tmp_path: Path) -> None:
        payload = _minimal_payload()
        payload["overview"] = "private-report-content-should-not-be-in-source-zip"
        out = build_html(payload)
        assert "表示プログラム:" in out
        assert "無保証" in out
        assert 'download="kouchou-ai-report-source.zip"' in out
        encoded = re.search(r'href="data:application/zip;base64,([^"]+)"', out)
        assert encoded is not None
        expected_license = (Path(__file__).parents[1] / "LICENSE").read_text(encoding="utf-8")
        assert 'href="https://www.gnu.org/licenses/agpl-3.0.html"' in out
        assert "GNU AFFERO GENERAL PUBLIC LICENSE" not in out
        with zipfile.ZipFile(io.BytesIO(base64.b64decode(encoded.group(1)))) as bundle:
            assert set(bundle.namelist()) == {"hierarchical_visualization.py", "AGPL-3.0.txt", "README.md"}
            assert bundle.read("AGPL-3.0.txt").decode("utf-8") == expected_license
            for name in bundle.namelist():
                assert payload["overview"].encode() not in bundle.read(name)
            bundle.extractall(tmp_path)
        result_json = tmp_path / "result.json"
        result_json.write_text(json.dumps(payload), encoding="utf-8")
        rebuilt = tmp_path / "rebuilt.html"
        # Isolated Python ignores PYTHONPATH and site-packages: stdlib alone suffices.
        subprocess.run(
            [sys.executable, "-I", "-S", str(tmp_path / "hierarchical_visualization.py"),
             str(result_json), "-o", str(rebuilt)],
            check=True, capture_output=True, text=True,
        )
        assert rebuilt.read_text(encoding="utf-8") == out

    def test_bundle_preserves_local_source_edits(self, tmp_path: Path, monkeypatch) -> None:
        import importlib

        module = importlib.import_module("analysis_core.steps.hierarchical_visualization")
        source = Path(module.__file__).read_text(encoding="utf-8") + "\n# local viewer modification\n"
        renderer = tmp_path / "hierarchical_visualization.py"
        renderer.write_text(source, encoding="utf-8")
        (tmp_path / "AGPL-3.0.txt").write_bytes((Path(__file__).parents[1] / "LICENSE").read_bytes())
        monkeypatch.setattr(module, "__file__", str(renderer))
        out = module.build_html(_minimal_payload())
        encoded = re.search(r'href="data:application/zip;base64,([^"]+)"', out)
        assert encoded is not None
        with zipfile.ZipFile(io.BytesIO(base64.b64decode(encoded.group(1)))) as bundle:
            assert bundle.read("hierarchical_visualization.py").decode("utf-8") == source

    def test_missing_license_degrades_to_link_only_notice(self, tmp_path: Path, monkeypatch) -> None:
        import importlib

        module = importlib.import_module("analysis_core.steps.hierarchical_visualization")
        # Point __file__ at a tmp dir with no sibling AGPL-3.0.txt and no
        # pyproject.toml/LICENSE fallback above it, so neither resource resolves.
        renderer = tmp_path / "hierarchical_visualization.py"
        renderer.write_text(Path(module.__file__).read_text(encoding="utf-8"), encoding="utf-8")
        monkeypatch.setattr(module, "__file__", str(renderer))
        # Report generation must still succeed, not raise FileNotFoundError.
        out = module.build_html(_minimal_payload())
        assert "表示プログラム:" in out
        assert "無保証" in out
        assert 'href="https://www.gnu.org/licenses/agpl-3.0.html"' in out
        # The source ZIP is omitted when its inputs are unavailable.
        assert "data:application/zip;base64," not in out
        assert 'download="kouchou-ai-report-source.zip"' not in out


def _arg_items(out: str) -> list[str]:
    """意見リスト（ul.args）の li の中身だけを、出現順に返す。"""
    items: list[str] = []
    for block in re.findall(r'<ul class="args">(.*?)</ul>', out, flags=re.S):
        items.extend(re.findall(r"<li>(.*?)</li>", block, flags=re.S))
    return items


class TestArgumentListsInTree:
    """意見の一覧が、木の葉（子を持たないクラスタ）ごとに 1 回ずつ出ること。"""

    def test_single_level_tree_lists_arguments_under_level1(self) -> None:
        # llm_grouping や cluster_nums が 1 要素の場合のように、level 1 が葉になる木
        out = build_html(_minimal_payload())
        items = _arg_items(out)
        assert len(items) == 2
        assert any('<span class="comment-id">#1</span> alpha' in i for i in items)
        assert any('<span class="comment-id">#2</span> beta' in i for i in items)

    def test_single_level_tree_list_keeps_source_link(self) -> None:
        out = build_html(_minimal_payload(), url_pattern="https://example.com/r/{comment_id}")
        items = _arg_items(out)
        assert any('href="https://example.com/r/1"' in i for i in items)
        assert any('href="https://example.com/r/2"' in i for i in items)

    def test_single_level_tree_list_drops_non_http_source_link(self) -> None:
        payload = _minimal_payload()
        payload["arguments"][0]["url"] = "javascript:alert(1)"
        payload["arguments"][1]["url"] = "https://example.com/ok"
        # build_html を通さず木だけを描いても、level 1 の一覧で http(s) 以外のリンクを出さない
        for out in (build_html(payload), _render_tree(payload)):
            items = _arg_items(out)
            assert len(items) == 2
            assert not any("javascript:" in i.lower() for i in items)
            assert any('href="https://example.com/ok"' in i for i in items)

    def test_two_level_tree_lists_each_argument_once(self) -> None:
        payload = _minimal_payload()
        payload["arguments"][0]["cluster_ids"] = ["0", "1_1", "2_1"]
        payload["arguments"][1]["cluster_ids"] = ["0", "1_2", "2_2"]
        payload["clusters"] += [
            {"id": "2_1", "level": 2, "label": "alpha sub", "value": 1, "parent": "1_1", "takeaway": ""},
            {"id": "2_2", "level": 2, "label": "beta sub", "value": 1, "parent": "1_2", "takeaway": ""},
        ]
        out = build_html(payload)
        items = _arg_items(out)
        # level 1 では重ねて出さず、葉の level 2 にだけ出る
        assert len(items) == 2

    def test_mixed_tree_lists_arguments_for_childless_level1(self) -> None:
        payload = _minimal_payload()
        payload["arguments"][0]["cluster_ids"] = ["0", "1_1", "2_1"]
        payload["clusters"].append(
            {"id": "2_1", "level": 2, "label": "alpha sub", "value": 1, "parent": "1_1", "takeaway": ""}
        )
        out = build_html(payload)
        items = _arg_items(out)
        assert len(items) == 2
        assert sum("alpha" in i for i in items) == 1
        assert sum("beta" in i for i in items) == 1
