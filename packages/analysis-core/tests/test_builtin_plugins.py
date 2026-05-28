"""Regression tests for built-in analysis plugins."""

import importlib

from analysis_core.plugin import StepContext, StepInputs
from analysis_core.plugins.builtin.extraction import extraction_plugin
from analysis_core.plugins.builtin.hierarchical_layout_generation import hierarchical_layout_generation_plugin
from analysis_core.plugins.builtin.hierarchical_visualization import hierarchical_visualization_plugin


def test_visualization_plugin_reports_report_html_path(tmp_path, monkeypatch):
    """The workflow plugin should match the current step output contract."""

    output_dir = tmp_path / "out"
    input_dir = tmp_path / "in"
    output_dir.mkdir()
    input_dir.mkdir()

    ctx = StepContext(
        output_dir=output_dir,
        input_dir=input_dir,
        dataset="demo",
        provider="local",
        model="dummy",
    )

    def fake_visualization(config):
        assert config["report_html_title"] == "Workflow Report"
        assert config["report_url_pattern"] == "https://example.com/{comment_id}"
        (output_dir / "report.html").write_text("<html></html>", encoding="utf-8")

    viz_module = importlib.import_module("analysis_core.steps.hierarchical_visualization")
    monkeypatch.setattr(viz_module, "hierarchical_visualization", fake_visualization)

    outputs = hierarchical_visualization_plugin.run(
        ctx,
        StepInputs(),
        {
            "hierarchical_visualization": {
                "report_html_title": "Workflow Report",
                "report_url_pattern": "https://example.com/{comment_id}",
            }
        },
    )

    assert outputs.artifacts["html"] == output_dir / "report.html"


def test_layout_generation_plugin_reports_result_path(tmp_path, monkeypatch):
    """Layout generation mutates hierarchical_result.json in place."""

    output_dir = tmp_path / "out"
    input_dir = tmp_path / "in"
    output_dir.mkdir()
    input_dir.mkdir()

    ctx = StepContext(
        output_dir=output_dir,
        input_dir=input_dir,
        dataset="demo",
        provider="local",
        model="dummy",
    )

    seen = {}

    def fake_layout_generation(config):
        seen.update(config)
        (output_dir / "hierarchical_result.json").write_text("{}", encoding="utf-8")

    layout_module = importlib.import_module("analysis_core.steps.hierarchical_layout_generation")
    monkeypatch.setattr(layout_module, "hierarchical_layout_generation", fake_layout_generation)

    outputs = hierarchical_layout_generation_plugin.run(
        ctx,
        StepInputs(
            artifacts={
                "result": output_dir / "hierarchical_result.json",
                "embeddings": output_dir / "embeddings.pkl",
            },
            config={"analysis_mode": "llm_grouping"},
        ),
        {
            "layout_generation": {
                "default_layout": "semantic_island_map",
            }
        },
    )

    assert seen["layout_generation"]["default_layout"] == "semantic_island_map"
    assert outputs.artifacts["result"] == output_dir / "hierarchical_result.json"


def test_extraction_plugin_keeps_explicit_input_over_comments_fallback(tmp_path, monkeypatch):
    """Explicit configured input should win over comments-derived fallback."""

    output_dir = tmp_path / "custom-output" / "demo"
    input_dir = tmp_path / "custom-input"
    comments_dir = input_dir / "nested"
    comments_path = comments_dir / "sample-comments.csv"
    output_dir.mkdir(parents=True)
    comments_dir.mkdir(parents=True)
    comments_path.write_text("comment-id,comment-body\n1,test\n", encoding="utf-8")

    ctx = StepContext(
        output_dir=output_dir,
        input_dir=input_dir,
        dataset="demo",
        provider="local",
        model="dummy-model",
        local_llm_address="127.0.0.1:9999",
        user_api_key="ctx-user-key",
    )

    seen = {}

    def fake_extraction(config):
        seen.update(config)
        (output_dir / "args.csv").write_text("arg-id,argument\na1,test\n", encoding="utf-8")
        (output_dir / "relations.csv").write_text("arg-id,comment-id\na1,1\n", encoding="utf-8")

    extraction_module = importlib.import_module("analysis_core.steps.extraction")
    monkeypatch.setattr(extraction_module, "extraction", fake_extraction)

    outputs = extraction_plugin.run(
        ctx,
        StepInputs(
            artifacts={"comments": comments_path},
            config={"input": "configured-input"},
        ),
        {
            "extraction": {
                "model": "test-model",
                "prompt": "extract",
                "workers": 2,
                "limit": 10,
                "properties": [],
            }
        },
    )

    assert seen["input"] == "configured-input"
    assert seen["_input_base_dir"] == str(input_dir)
    assert seen["_output_base_dir"] == str(output_dir.parent)
    assert seen["user_api_key"] == "ctx-user-key"
    assert outputs.artifacts["arguments"] == output_dir / "args.csv"
    assert outputs.artifacts["relations"] == output_dir / "relations.csv"


def test_extraction_plugin_uses_comments_path_as_input_fallback(tmp_path, monkeypatch):
    """Comments artifact should provide input slug and base dir when config omits it."""

    output_dir = tmp_path / "custom-output" / "demo"
    input_dir = tmp_path / "custom-input"
    comments_dir = input_dir / "nested"
    comments_path = comments_dir / "sample-comments.csv"
    output_dir.mkdir(parents=True)
    comments_dir.mkdir(parents=True)
    comments_path.write_text("comment-id,comment-body\n1,test\n", encoding="utf-8")

    ctx = StepContext(
        output_dir=output_dir,
        input_dir=input_dir,
        dataset="demo",
        provider="local",
        model="dummy-model",
        local_llm_address="127.0.0.1:9999",
    )

    seen = {}

    def fake_extraction(config):
        seen.update(config)
        (output_dir / "args.csv").write_text("arg-id,argument\na1,test\n", encoding="utf-8")
        (output_dir / "relations.csv").write_text("arg-id,comment-id\na1,1\n", encoding="utf-8")

    extraction_module = importlib.import_module("analysis_core.steps.extraction")
    monkeypatch.setattr(extraction_module, "extraction", fake_extraction)

    outputs = extraction_plugin.run(
        ctx,
        StepInputs(
            artifacts={"comments": comments_path},
            config={},
        ),
        {
            "extraction": {
                "model": "test-model",
                "prompt": "extract",
                "workers": 2,
                "limit": 10,
                "properties": [],
            }
        },
    )

    assert seen["input"] == "sample-comments"
    assert seen["_input_base_dir"] == str(comments_dir)
    assert seen["_output_base_dir"] == str(output_dir.parent)
    assert outputs.artifacts["arguments"] == output_dir / "args.csv"
    assert outputs.artifacts["relations"] == output_dir / "relations.csv"
