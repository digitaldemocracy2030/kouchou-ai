"""
Pre-defined workflow definitions.

This module provides ready-to-use workflow definitions for common
analysis patterns.
"""

from analysis_core.workflows.hierarchical_default import (
    HIERARCHICAL_DEFAULT_WORKFLOW,
    create_hierarchical_workflow,
)

__all__ = [
    "HIERARCHICAL_DEFAULT_WORKFLOW",
    "create_hierarchical_workflow",
]
