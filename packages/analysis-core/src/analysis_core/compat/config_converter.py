"""
Configuration converter for legacy format compatibility.

This module provides utilities to convert legacy pipeline configurations
to the new workflow-based format while maintaining backwards compatibility.
"""

from typing import Any

from analysis_core.prompts import get_default_prompt
from analysis_core.workflow import WorkflowDefinition
from analysis_core.workflows import HIERARCHICAL_DEFAULT_WORKFLOW


def normalize_config(config: dict[str, Any]) -> dict[str, Any]:
    """
    Normalize a configuration by filling in defaults.

    Takes a potentially incomplete configuration and fills in
    default values for missing fields.

    Args:
        config: Input configuration (potentially incomplete)

    Returns:
        Complete configuration with all defaults filled in
    """
    # Copy to avoid mutating input
    result = config.copy()

    # Top-level defaults
    result.setdefault("model", "gpt-4o-mini")
    result.setdefault("provider", "openai")
    result.setdefault("is_embedded_at_local", False)
    result.setdefault("is_pubcom", False)
    result.setdefault("intro", "")
    result.setdefault("enable_source_link", False)
    result.setdefault("without_html", True)

    # Extraction defaults
    extraction = result.setdefault("extraction", {})
    extraction.setdefault("limit", 1000)
    extraction.setdefault("workers", 3)
    extraction.setdefault("prompt", get_default_prompt("extraction") or "")
    extraction.setdefault("model", result["model"])
    extraction.setdefault("properties", [])
    extraction.setdefault("categories", {})

    # Embedding defaults
    embedding = result.setdefault("embedding", {})
    embedding.setdefault("model", "text-embedding-3-small")

    # Hierarchical clustering defaults
    clustering = result.setdefault("hierarchical_clustering", {})
    clustering.setdefault("cluster_nums", [3, 6])

    # Initial labelling defaults
    initial_labelling = result.setdefault("hierarchical_initial_labelling", {})
    initial_labelling.setdefault("sampling_num", 10)
    initial_labelling.setdefault("prompt", get_default_prompt("hierarchical_initial_labelling") or "")
    initial_labelling.setdefault("model", result["model"])
    initial_labelling.setdefault("workers", 3)

    # Merge labelling defaults
    merge_labelling = result.setdefault("hierarchical_merge_labelling", {})
    merge_labelling.setdefault("sampling_num", 10)
    merge_labelling.setdefault("prompt", get_default_prompt("hierarchical_merge_labelling") or "")
    merge_labelling.setdefault("model", result["model"])
    merge_labelling.setdefault("workers", 3)

    # Overview defaults
    overview = result.setdefault("hierarchical_overview", {})
    overview.setdefault("prompt", get_default_prompt("hierarchical_overview") or "")
    overview.setdefault("model", result["model"])

    # Aggregation defaults
    aggregation = result.setdefault("hierarchical_aggregation", {})
    aggregation.setdefault("hidden_properties", {})

    return result


def convert_legacy_config(
    legacy_config: dict[str, Any],
) -> tuple[WorkflowDefinition, dict[str, Any]]:
    """
    Convert a legacy configuration to the new workflow format.

    Takes a configuration in the old format and returns a tuple of
    (workflow_definition, normalized_config).

    Args:
        legacy_config: Configuration in the legacy format

    Returns:
        Tuple of (workflow_definition, normalized_config)
    """
    # Normalize the config first
    normalized = normalize_config(legacy_config)

    # Use the default hierarchical workflow
    # In the future, we could detect different workflow types from config
    workflow = HIERARCHICAL_DEFAULT_WORKFLOW

    return workflow, normalized


def create_step_context_from_config(
    config: dict[str, Any],
    output_dir: str | None = None,
    input_dir: str = "inputs",
    output_base_dir: str = "outputs",
):
    """
    Create a StepContext from a legacy configuration.

    Args:
        config: Normalized configuration
        output_dir: Output directory name (defaults to config["output_dir"])
        input_dir: Base input directory
        output_base_dir: Base output directory

    Returns:
        StepContext for workflow execution
    """
    from pathlib import Path

    from analysis_core.plugin import StepContext

    dataset = output_dir or config.get("output_dir", config.get("name", "analysis"))

    return StepContext(
        output_dir=Path(output_base_dir) / dataset,
        input_dir=Path(input_dir),
        dataset=dataset,
        provider=config.get("provider", "openai"),
        model=config.get("model", "gpt-4o-mini"),
        local_llm_address=config.get("local_llm_address"),
        user_api_key=config.get("user_api_key"),
    )
