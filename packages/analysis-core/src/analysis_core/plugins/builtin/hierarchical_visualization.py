"""
Hierarchical visualization step plugin.

Generates HTML visualization using npm build.
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
    description="Generate HTML visualization using npm build",
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

    Uses npm to build an interactive HTML visualization from the
    analysis results.

    Config options:
        - report_dir: Path to the report directory (default: "../report")
    """
    from analysis_core.steps.hierarchical_visualization import (
        hierarchical_visualization as viz_impl,
    )

    step_config = config.get("hierarchical_visualization", config)
    legacy_config = {
        "output_dir": ctx.dataset,
        "report_dir": step_config.get("report_dir", "../report"),
    }

    viz_impl(legacy_config)

    # Use ctx.output_dir which already contains the full path
    return StepOutputs(
        artifacts={
            "html": ctx.output_dir / "index.html",
        },
    )
