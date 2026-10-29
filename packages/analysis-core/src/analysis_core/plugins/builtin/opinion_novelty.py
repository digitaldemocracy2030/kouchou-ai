"""
Opinion novelty step plugin.

Attaches a novelty score (0.0 .. 1.0, higher = farther from the other opinions in
embedding space) to each extracted opinion. No LLM call.
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
    id="analysis.opinion_novelty",
    version="1.0.0",
    name="Opinion Novelty",
    description="Score how far each extracted opinion is from the others in embedding space",
    inputs=["arguments", "embeddings"],
    outputs=["novelty", "novelty_summary"],
    use_llm=False,
)
def opinion_novelty_plugin(
    ctx: StepContext,
    inputs: StepInputs,
    config: dict[str, Any],
) -> StepOutputs:
    """
    Score extracted opinions by novelty.

    Config options:
        - method: knn_distance (default) or isolation_forest
        - k: Number of neighbours for knn_distance
        - seed: Random seed for isolation_forest
    """
    from analysis_core.steps.opinion_novelty import (
        NOVELTY_FILENAME,
        SUMMARY_FILENAME,
    )
    from analysis_core.steps.opinion_novelty import (
        opinion_novelty as novelty_impl,
    )

    step_config = config.get("opinion_novelty", config)
    legacy_config = build_legacy_runtime_config(ctx, inputs)
    legacy_config["opinion_novelty"] = {
        "method": step_config.get("method"),
        "k": step_config.get("k"),
        "seed": step_config.get("seed"),
    }

    novelty_impl(legacy_config)

    return StepOutputs(
        artifacts={
            "novelty": ctx.output_dir / NOVELTY_FILENAME,
            "novelty_summary": ctx.output_dir / SUMMARY_FILENAME,
        },
    )
