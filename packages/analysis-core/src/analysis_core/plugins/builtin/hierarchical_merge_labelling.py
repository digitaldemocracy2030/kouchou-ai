"""
Hierarchical merge labelling step plugin.

Merges and labels higher-level clusters by combining lower-level labels.
"""

from pathlib import Path
from typing import Any

from analysis_core.plugin import (
    PluginMetadata,
    StepContext,
    StepInputs,
    StepOutputs,
    step_plugin,
)


@step_plugin(
    id="analysis.hierarchical_merge_labelling",
    version="1.0.0",
    name="Hierarchical Merge Labelling",
    description="Merge and label higher-level clusters from lower-level labels",
    inputs=["initial_labels"],
    outputs=["merge_labels"],
    use_llm=True,
)
def hierarchical_merge_labelling_plugin(
    ctx: StepContext,
    inputs: StepInputs,
    config: dict[str, Any],
) -> StepOutputs:
    """
    Generate labels for merged (parent) clusters.

    Combines child cluster labels and sampled arguments to create
    labels for parent clusters at each hierarchy level.

    Config options:
        - sampling_num: Number of arguments to sample per cluster
        - prompt: System prompt for merge labelling
        - model: LLM model to use
        - workers: Number of parallel workers
    """
    from analysis_core.steps.hierarchical_merge_labelling import (
        hierarchical_merge_labelling as merge_impl,
    )

    step_config = config.get("hierarchical_merge_labelling", config)
    legacy_config = {
        "output_dir": ctx.dataset,
        "provider": ctx.provider,
        "local_llm_address": ctx.local_llm_address,
        "hierarchical_merge_labelling": {
            "sampling_num": step_config.get("sampling_num", 10),
            "prompt": step_config.get("prompt", ""),
            "model": step_config.get("model", ctx.model),
            "workers": step_config.get("workers", 3),
        },
        # Token tracking
        "total_token_usage": 0,
        "token_usage_input": 0,
        "token_usage_output": 0,
    }

    merge_impl(legacy_config)

    output_dir = Path("outputs") / ctx.dataset
    return StepOutputs(
        artifacts={
            "merge_labels": output_dir / "hierarchical_merge_labels.csv",
        },
        token_usage=legacy_config.get("total_token_usage", 0),
        token_input=legacy_config.get("token_usage_input", 0),
        token_output=legacy_config.get("token_usage_output", 0),
    )
