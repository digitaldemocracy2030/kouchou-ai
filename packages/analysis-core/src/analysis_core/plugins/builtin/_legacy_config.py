"""Helpers for adapting workflow context to legacy step configs."""

from pathlib import Path
from typing import Any

from analysis_core.plugin import StepContext, StepInputs


def build_legacy_runtime_config(
    ctx: StepContext,
    inputs: StepInputs | None = None,
    *,
    include_input: bool = False,
    include_token_usage: bool = False,
) -> dict[str, Any]:
    """Build the common runtime keys legacy step functions expect."""
    legacy_config: dict[str, Any] = {
        "output_dir": ctx.dataset,
        "_output_base_dir": str(ctx.output_dir.parent),
        "provider": ctx.provider,
        "local_llm_address": ctx.local_llm_address,
    }
    if ctx.user_api_key:
        legacy_config["user_api_key"] = ctx.user_api_key

    if include_input:
        input_name, input_base_dir = resolve_input_location(ctx, inputs)
        legacy_config["input"] = input_name
        legacy_config["_input_base_dir"] = str(input_base_dir)

    if include_token_usage:
        legacy_config.update(
            {
                "total_token_usage": 0,
                "token_usage_input": 0,
                "token_usage_output": 0,
            }
        )

    return legacy_config


def resolve_input_location(
    ctx: StepContext,
    inputs: StepInputs | None,
) -> tuple[str, Path]:
    """Resolve the input slug and base directory from workflow inputs."""
    input_name = ctx.dataset
    input_base_dir = ctx.input_dir

    if inputs is not None:
        configured_input = inputs.config.get("input")
        if isinstance(configured_input, str) and configured_input:
            input_name = configured_input

        comments_path = inputs.artifacts.get("comments")
        if not (isinstance(configured_input, str) and configured_input) and comments_path is not None:
            comments_path = Path(comments_path)
            input_name = comments_path.stem
            input_base_dir = comments_path.parent

    return input_name, input_base_dir
