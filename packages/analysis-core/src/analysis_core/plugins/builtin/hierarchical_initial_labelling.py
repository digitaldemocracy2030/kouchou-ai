"""
Hierarchical initial labelling step plugin.

Labels the finest-grained clusters using LLM.
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
    id="analysis.hierarchical_initial_labelling",
    version="1.0.0",
    name="Hierarchical Initial Labelling",
    description="Label the finest-grained clusters using LLM",
    inputs=["clusters"],
    outputs=["initial_labels"],
    use_llm=True,
)
def hierarchical_initial_labelling_plugin(
    ctx: StepContext,
    inputs: StepInputs,
    config: dict[str, Any],
) -> StepOutputs:
    """
    Generate labels for initial (leaf) clusters.

    Samples arguments from each cluster and uses LLM to generate
    descriptive labels and descriptions.

    Config options:
        - sampling_num: Number of arguments to sample per cluster
        - prompt: System prompt for labelling
        - model: LLM model to use
        - workers: Number of parallel workers
    """
    from analysis_core.steps.hierarchical_initial_labelling import (
        hierarchical_initial_labelling as labelling_impl,
    )

    step_config = config.get("hierarchical_initial_labelling", config)
    legacy_config = {
        "output_dir": ctx.dataset,
        "provider": ctx.provider,
        "local_llm_address": ctx.local_llm_address,
        "hierarchical_initial_labelling": {
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

    labelling_impl(legacy_config)

    output_dir = Path("outputs") / ctx.dataset
    return StepOutputs(
        artifacts={
            "initial_labels": output_dir / "hierarchical_initial_labels.csv",
        },
        token_usage=legacy_config.get("total_token_usage", 0),
        token_input=legacy_config.get("token_usage_input", 0),
        token_output=legacy_config.get("token_usage_output", 0),
    )
