"""
Compatibility layer for legacy configuration formats.

This module provides utilities for converting legacy configuration
formats to the new workflow-based format.
"""

from analysis_core.compat.config_converter import (
    convert_legacy_config,
    create_step_context_from_config,
    normalize_config,
)

__all__ = [
    "convert_legacy_config",
    "create_step_context_from_config",
    "normalize_config",
]
