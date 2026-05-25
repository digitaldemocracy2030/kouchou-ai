"""LLM grouping step plugin."""

from typing import Any

from analysis_core.plugin import StepContext, StepInputs, StepOutputs, step_plugin
from analysis_core.plugins.builtin._legacy_config import build_legacy_runtime_config


@step_plugin(
    id="analysis.llm_grouping",
    version="1.0.0",
    name="LLM Grouping",
    description="Assign arguments to top-level groups with LLM while preserving embedding-based coordinates",
    inputs=["arguments", "embeddings"],
    outputs=["clusters", "merge_labels"],
    use_llm=True,
)
def llm_grouping_plugin(
    ctx: StepContext,
    inputs: StepInputs,
    config: dict[str, Any],
) -> StepOutputs:
    """Run LLM-driven grouping and emit viewer-compatible cluster artifacts."""
    from analysis_core.steps.llm_grouping import llm_grouping as grouping_impl

    step_config = config.get("llm_grouping", config)
    legacy_config = build_legacy_runtime_config(ctx, inputs, include_token_usage=True)
    legacy_config["question"] = inputs.config.get("question", "")
    legacy_config["hierarchical_clustering"] = inputs.config.get("hierarchical_clustering", {})
    legacy_config["llm_grouping"] = {
        "group_count": step_config.get("group_count"),
        "discovery_sample_size": step_config.get("discovery_sample_size", 80),
        "assignment_batch_size": step_config.get("assignment_batch_size", 25),
        "discovery_prompt": step_config.get("discovery_prompt", ""),
        "assignment_prompt": step_config.get("assignment_prompt", ""),
        "model": step_config.get("model", ctx.model),
    }

    grouping_impl(legacy_config)

    return StepOutputs(
        artifacts={
            "clusters": ctx.output_dir / "hierarchical_clusters.csv",
            "merge_labels": ctx.output_dir / "hierarchical_merge_labels.csv",
        },
        token_usage=legacy_config.get("total_token_usage", 0),
        token_input=legacy_config.get("token_usage_input", 0),
        token_output=legacy_config.get("token_usage_output", 0),
    )
