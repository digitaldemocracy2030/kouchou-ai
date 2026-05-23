"""Regression tests for built-in analysis plugins."""

import importlib

from analysis_core.plugin import StepContext, StepInputs
from analysis_core.plugins.builtin.extraction import extraction_plugin
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


def test_extraction_plugin_passes_resolved_input_and_output_paths(tmp_path, monkeypatch):
    """The workflow plugin should pass input/output base dirs to legacy steps."""

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
            config={"input": "ignored-by-comments-artifact"},
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
