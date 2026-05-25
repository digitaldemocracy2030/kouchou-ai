"""Pipeline step implementations."""

from importlib import import_module
from typing import Any

_STEP_MODULES = {
    "embedding": "analysis_core.steps.embedding",
    "extraction": "analysis_core.steps.extraction",
    "hierarchical_aggregation": "analysis_core.steps.hierarchical_aggregation",
    "hierarchical_clustering": "analysis_core.steps.hierarchical_clustering",
    "hierarchical_initial_labelling": "analysis_core.steps.hierarchical_initial_labelling",
    "hierarchical_merge_labelling": "analysis_core.steps.hierarchical_merge_labelling",
    "hierarchical_overview": "analysis_core.steps.hierarchical_overview",
    "hierarchical_visualization": "analysis_core.steps.hierarchical_visualization",
    "llm_grouping": "analysis_core.steps.llm_grouping",
}

__all__ = [
    "extraction",
    "embedding",
    "hierarchical_clustering",
    "hierarchical_initial_labelling",
    "hierarchical_merge_labelling",
    "hierarchical_overview",
    "hierarchical_aggregation",
    "hierarchical_visualization",
    "llm_grouping",
]


def __getattr__(name: str) -> Any:
    """Lazily load step modules so base installs can import analysis_core."""
    module_path = _STEP_MODULES.get(name)
    if module_path is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

    module = import_module(module_path)
    value = getattr(module, name)
    globals()[name] = value
    return value
