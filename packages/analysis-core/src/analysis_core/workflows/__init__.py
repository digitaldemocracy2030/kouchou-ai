"""
Pre-defined workflow definitions.

This module provides ready-to-use workflow definitions for common
analysis patterns.
"""

from analysis_core.workflows.hierarchical_default import (
    HIERARCHICAL_DEFAULT_WORKFLOW,
    create_hierarchical_workflow,
)
from analysis_core.workflows.llm_grouping_compatible import (
    LLM_GROUPING_COMPATIBLE_WORKFLOW,
    create_llm_grouping_workflow,
)


def get_workflow_for_mode(analysis_mode: str):
    """Return the canonical workflow for a given analysis mode."""
    if analysis_mode == "llm_grouping":
        return LLM_GROUPING_COMPATIBLE_WORKFLOW
    return HIERARCHICAL_DEFAULT_WORKFLOW

__all__ = [
    "HIERARCHICAL_DEFAULT_WORKFLOW",
    "create_hierarchical_workflow",
    "LLM_GROUPING_COMPATIBLE_WORKFLOW",
    "create_llm_grouping_workflow",
    "get_workflow_for_mode",
]
