"""
Hierarchical aggregation step plugin.

Aggregates all results into a final JSON output file.
"""

from typing import Any

from analysis_core.plugin import (
    StepContext,
    StepInputs,
    StepOutputs,
    step_plugin,
)


@step_plugin(
    id="analysis.hierarchical_aggregation",
    version="1.0.0",
    name="Hierarchical Aggregation",
    description="Aggregate all results into a final JSON output file",
    inputs=["arguments", "clusters", "merge_labels", "overview"],
    outputs=["result"],
    use_llm=False,
)
def hierarchical_aggregation_plugin(
    ctx: StepContext,
    inputs: StepInputs,
    config: dict[str, Any],
) -> StepOutputs:
    """
    Aggregate all analysis results into final output.

    Combines arguments, clusters, labels, and overview into a
    structured JSON file ready for visualization.

    Config options:
        - hidden_properties: Properties to hide in output
    """
    from analysis_core.steps.hierarchical_aggregation import (
        hierarchical_aggregation as aggregation_impl,
    )

    step_config = config.get("hierarchical_aggregation", config)

    # Build legacy config - aggregation needs many fields from full config
    legacy_config = inputs.config.copy() if inputs.config else {}
    legacy_config.update({
        "output_dir": ctx.dataset,
        "input": inputs.config.get("input", ctx.dataset),
        "provider": ctx.provider,
        "hierarchical_aggregation": {
            "hidden_properties": step_config.get("hidden_properties", {}),
        },
    })

    # Ensure required fields exist
    if "extraction" not in legacy_config:
        legacy_config["extraction"] = {"limit": 1000, "categories": {}}
    if "intro" not in legacy_config:
        legacy_config["intro"] = ""
    if "is_pubcom" not in legacy_config:
        legacy_config["is_pubcom"] = False
    if "model" not in legacy_config:
        legacy_config["model"] = ctx.model

    success = aggregation_impl(legacy_config)

    # Use ctx.output_dir which already contains the full path
    return StepOutputs(
        artifacts={
            "result": ctx.output_dir / "hierarchical_result.json",
        },
        metadata={
            "success": success,
        },
    )
