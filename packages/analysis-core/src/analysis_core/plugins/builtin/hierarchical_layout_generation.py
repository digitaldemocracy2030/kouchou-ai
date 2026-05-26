"""Derived layout generation plugin."""

from typing import Any

from analysis_core.plugin import StepContext, StepInputs, StepOutputs, step_plugin
from analysis_core.plugins.builtin._legacy_config import build_legacy_runtime_config


@step_plugin(
    id="analysis.hierarchical_layout_generation",
    version="1.0.0",
    name="Hierarchical Layout Generation",
    description="Generate additional named layouts for hierarchical_result.json",
    inputs=["result", "embeddings"],
    outputs=["result"],
    use_llm=False,
)
def hierarchical_layout_generation_plugin(
    ctx: StepContext,
    inputs: StepInputs,
    config: dict[str, Any],
) -> StepOutputs:
    from analysis_core.steps.hierarchical_layout_generation import hierarchical_layout_generation

    step_config = config.get("layout_generation", config)
    legacy_config = build_legacy_runtime_config(ctx, inputs)
    legacy_config["layout_generation"] = step_config

    hierarchical_layout_generation(legacy_config)

    return StepOutputs(
        artifacts={
            "result": ctx.output_dir / "hierarchical_result.json",
        }
    )
