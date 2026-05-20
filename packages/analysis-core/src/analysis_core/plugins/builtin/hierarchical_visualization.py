"""
Hierarchical visualization step plugin.

Generates the self-contained HTML visualization.
"""

from typing import Any

from analysis_core.plugin import (
    StepContext,
    StepInputs,
    StepOutputs,
    step_plugin,
)


@step_plugin(
    id="analysis.hierarchical_visualization",
    version="1.0.0",
    name="Hierarchical Visualization",
    description="Generate the self-contained HTML visualization",
    inputs=["result"],
    outputs=["html"],
    use_llm=False,
)
def hierarchical_visualization_plugin(
    ctx: StepContext,
    inputs: StepInputs,
    config: dict[str, Any],
) -> StepOutputs:
    """
    Generate HTML visualization.

    Uses the pure-Python visualization step to build a self-contained
    HTML report from the analysis results.

    Config options:
        - report_html_title: Override the HTML title
        - report_url_pattern: Optional URL pattern used for source links
    """
    from analysis_core.steps.hierarchical_visualization import (
        hierarchical_visualization as viz_impl,
    )

    step_config = config.get("hierarchical_visualization", config)
    legacy_config = {
        "output_dir": ctx.dataset,
        "report_dir": step_config.get("report_dir", "../report"),
        "report_html_title": step_config.get("report_html_title"),
        "report_url_pattern": step_config.get("report_url_pattern"),
    }

    viz_impl(legacy_config)

    # Use ctx.output_dir which already contains the full path
    return StepOutputs(
        artifacts={
            "html": ctx.output_dir / "report.html",
        },
    )
