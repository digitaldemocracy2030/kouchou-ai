"""
Hierarchical overview step plugin.

Creates an overall summary of all clusters using LLM.
"""

from typing import Any

from analysis_core.plugin import (
    StepContext,
    StepInputs,
    StepOutputs,
    step_plugin,
)
from analysis_core.plugins.builtin._legacy_config import build_legacy_runtime_config


@step_plugin(
    id="analysis.hierarchical_overview",
    version="1.0.0",
    name="Hierarchical Overview",
    description="Create an overall summary of all clusters using LLM",
    inputs=["merge_labels"],
    outputs=["overview"],
    use_llm=True,
)
def hierarchical_overview_plugin(
    ctx: StepContext,
    inputs: StepInputs,
    config: dict[str, Any],
) -> StepOutputs:
    """
    Generate an overview summary of all clusters.

    Takes the top-level cluster labels and descriptions and uses LLM
    to create a comprehensive summary.

    Config options:
        - prompt: System prompt for overview generation
        - model: LLM model to use
    """
    from analysis_core.steps.hierarchical_overview import (
        hierarchical_overview as overview_impl,
    )

    step_config = config.get("hierarchical_overview", config)
    legacy_config = build_legacy_runtime_config(ctx, inputs, include_token_usage=True)
    legacy_config["hierarchical_overview"] = {
        "prompt": step_config.get("prompt", ""),
        "model": step_config.get("model", ctx.model),
    }

    overview_impl(legacy_config)

    # Use ctx.output_dir which already contains the full path
    return StepOutputs(
        artifacts={
            "overview": ctx.output_dir / "hierarchical_overview.txt",
        },
        token_usage=legacy_config.get("total_token_usage", 0),
        token_input=legacy_config.get("token_usage_input", 0),
        token_output=legacy_config.get("token_usage_output", 0),
    )
