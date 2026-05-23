"""
Extraction step plugin.

Extracts opinions/arguments from comments using LLM.
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

    step_config = config.get("extraction", config)
    legacy_config = build_legacy_runtime_config(ctx, inputs, include_input=True, include_token_usage=True)
    legacy_config["extraction"] = {
        "model": step_config.get("model", ctx.model),
        "prompt": step_config.get("prompt", ""),
        "workers": step_config.get("workers", 1),
        "limit": step_config.get("limit", 1000),
        "properties": step_config.get("properties", []),
    }

    # Run the extraction
    extraction_impl(legacy_config)

    # Build outputs - use ctx.output_dir which already contains the full path
    return StepOutputs(
        artifacts={
            "arguments": ctx.output_dir / "args.csv",
            "relations": ctx.output_dir / "relations.csv",
        },
        token_usage=legacy_config.get("total_token_usage", 0),
        token_input=legacy_config.get("token_usage_input", 0),
        token_output=legacy_config.get("token_usage_output", 0),
    )
