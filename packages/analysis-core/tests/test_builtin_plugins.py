"""Regression tests for built-in analysis plugins."""

import importlib

from analysis_core.plugin import StepContext, StepInputs
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
