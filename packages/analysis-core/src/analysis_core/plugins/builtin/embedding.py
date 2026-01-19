"""
Embedding step plugin.

Creates vector embeddings for arguments using embedding models.
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
    id="analysis.embedding",
    version="1.0.0",
    name="Embedding",
    description="Create vector embeddings for arguments",
    inputs=["arguments"],
    outputs=["embeddings"],
    use_llm=False,  # Uses embedding API, not chat API
)
def embedding_plugin(
    ctx: StepContext,
    inputs: StepInputs,
    config: dict[str, Any],
) -> StepOutputs:
    """
    Create embeddings for extracted arguments.

    Reads arguments from args.csv, creates vector embeddings using the
    specified embedding model, and saves to embeddings.pkl.

    Config options:
        - model: Embedding model to use
    """
    from analysis_core.steps.embedding import embedding as embedding_impl

    step_config = config.get("embedding", config)
    legacy_config = {
        "output_dir": ctx.dataset,
        "provider": ctx.provider,
        "local_llm_address": ctx.local_llm_address,
        "is_embedded_at_local": inputs.config.get("is_embedded_at_local", False),
        "embedding": {
            "model": step_config.get("model", "text-embedding-3-small"),
        },
    }

    embedding_impl(legacy_config)

    output_dir = Path("outputs") / ctx.dataset
    return StepOutputs(
        artifacts={
            "embeddings": output_dir / "embeddings.pkl",
        },
    )
