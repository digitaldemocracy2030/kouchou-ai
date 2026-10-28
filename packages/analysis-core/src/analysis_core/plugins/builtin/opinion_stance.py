"""
Opinion stance step plugin.

Attaches a stance score (-1.0 .. +1.0 toward the report question or a configured
target) to each extracted opinion using an LLM.
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
    id="analysis.opinion_stance",
    version="1.0.0",
    name="Opinion Stance",
    description="Score each extracted opinion's stance (-1.0 .. +1.0) toward a target using LLM",
    inputs=["arguments"],
    outputs=["stances", "stance_summary"],
    use_llm=True,
)
def opinion_stance_plugin(
    ctx: StepContext,
    inputs: StepInputs,
    config: dict[str, Any],
) -> StepOutputs:
    """
    Score extracted opinions.

    Config options:
        - model: LLM model to use (default: from context)
        - prompt: System prompt with the scoring rules
        - workers: Number of parallel requests
        - target: What the stance is judged against (default: the report question)
        - timeout_seconds: Per-request timeout
    """
    from analysis_core.prompts import get_default_prompt
    from analysis_core.steps.opinion_stance import (
        STANCES_FILENAME,
        SUMMARY_FILENAME,
    )
    from analysis_core.steps.opinion_stance import (
        opinion_stance as stance_impl,
    )

    step_config = config.get("opinion_stance", config)
    legacy_config = build_legacy_runtime_config(ctx, inputs, include_token_usage=True)
    # target が無いときの既定の対象（レポートの question）
    legacy_config["question"] = step_config.get("question")
    legacy_config["opinion_stance"] = {
        "model": step_config.get("model") or ctx.model,
        "prompt": step_config.get("prompt") or get_default_prompt("opinion_stance"),
        "workers": step_config.get("workers", 1),
        "target": step_config.get("target"),
        "timeout_seconds": step_config.get("timeout_seconds"),
    }

    stance_impl(legacy_config)

    return StepOutputs(
        artifacts={
            "stances": ctx.output_dir / STANCES_FILENAME,
            "stance_summary": ctx.output_dir / SUMMARY_FILENAME,
        },
        token_usage=legacy_config.get("total_token_usage", 0),
        token_input=legacy_config.get("token_usage_input", 0),
        token_output=legacy_config.get("token_usage_output", 0),
    )
