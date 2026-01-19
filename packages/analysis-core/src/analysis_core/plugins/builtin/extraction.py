"""
Extraction step plugin.

Extracts opinions/arguments from comments using LLM.
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
    id="analysis.extraction",
    version="1.0.0",
    name="Extraction",
    description="Extract opinions/arguments from comments using LLM",
    inputs=["comments"],
    outputs=["arguments", "relations"],
    use_llm=True,
)
def extraction_plugin(
    ctx: StepContext,
    inputs: StepInputs,
    config: dict[str, Any],
) -> StepOutputs:
    """
    Extract opinions from comments.

    Reads comment data, uses LLM to extract individual opinions/arguments,
    and creates mapping between comments and extracted arguments.

    Config options:
        - model: LLM model to use (default: from context)
        - prompt: System prompt for extraction
        - workers: Number of parallel workers
        - limit: Maximum comments to process
        - properties: Additional property columns to include
    """
    # Import here to avoid circular imports
    from analysis_core.steps.extraction import extraction as extraction_impl

    # Build legacy config format for compatibility
    step_config = config.get("extraction", config)
    legacy_config = {
        "output_dir": ctx.dataset,
        "input": inputs.config.get("input", ctx.dataset),
        "provider": ctx.provider,
        "local_llm_address": ctx.local_llm_address,
        "extraction": {
            "model": step_config.get("model", ctx.model),
            "prompt": step_config.get("prompt", ""),
            "workers": step_config.get("workers", 1),
            "limit": step_config.get("limit", 1000),
            "properties": step_config.get("properties", []),
        },
        # Token tracking
        "total_token_usage": 0,
        "token_usage_input": 0,
        "token_usage_output": 0,
    }

    # Run the extraction
    extraction_impl(legacy_config)

    # Build outputs
    output_dir = Path("outputs") / ctx.dataset
    return StepOutputs(
        artifacts={
            "arguments": output_dir / "args.csv",
            "relations": output_dir / "relations.csv",
        },
        token_usage=legacy_config.get("total_token_usage", 0),
        token_input=legacy_config.get("token_usage_input", 0),
        token_output=legacy_config.get("token_usage_output", 0),
    )
