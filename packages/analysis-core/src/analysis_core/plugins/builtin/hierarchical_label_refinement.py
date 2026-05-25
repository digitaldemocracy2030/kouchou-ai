"""Hierarchical top-level label refinement plugin."""

from typing import Any

from analysis_core.plugin import StepContext, StepInputs, StepOutputs, step_plugin
from analysis_core.plugins.builtin._legacy_config import build_legacy_runtime_config


@step_plugin(
    id="analysis.hierarchical_label_refinement",
    version="1.0.0",
    name="Hierarchical Label Refinement",
    description="Refine top-level cluster labels as a set for readability and distinctiveness",
    inputs=["merge_labels"],
    outputs=["merge_labels"],
    use_llm=True,
)
def hierarchical_label_refinement_plugin(
    ctx: StepContext,
    inputs: StepInputs,
    config: dict[str, Any],
) -> StepOutputs:
    """Refine top-level labels while keeping the existing cluster structure intact."""
    from analysis_core.steps.hierarchical_label_refinement import (
        hierarchical_label_refinement as refinement_impl,
    )

    step_config = config.get("hierarchical_label_refinement", config)
    legacy_config = build_legacy_runtime_config(ctx, inputs, include_token_usage=True)
    legacy_config["hierarchical_label_refinement"] = {
        "mode": step_config.get("mode", "none"),
        "prompt": step_config.get("prompt", ""),
        "model": step_config.get("model", ctx.model),
        "max_label_length": step_config.get("max_label_length", 24),
    }

    refinement_impl(legacy_config)

    return StepOutputs(
        artifacts={
            "merge_labels": ctx.output_dir / "hierarchical_merge_labels.csv",
        },
        token_usage=legacy_config.get("total_token_usage", 0),
        token_input=legacy_config.get("token_usage_input", 0),
        token_output=legacy_config.get("token_usage_output", 0),
    )
