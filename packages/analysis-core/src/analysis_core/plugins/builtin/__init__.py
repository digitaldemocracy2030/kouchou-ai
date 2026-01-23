"""
Built-in analysis step plugins.

This module registers the standard analysis steps as plugins.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from analysis_core.plugin.registry import PluginRegistry


def register_all(registry: "PluginRegistry") -> None:
    """
    Register all built-in plugins with the registry.

    This function registers the 8 standard analysis steps:
    - analysis.extraction
    - analysis.embedding
    - analysis.hierarchical_clustering
    - analysis.hierarchical_initial_labelling
    - analysis.hierarchical_merge_labelling
    - analysis.hierarchical_overview
    - analysis.hierarchical_aggregation
    - analysis.hierarchical_visualization

    Args:
        registry: Plugin registry to register plugins with
    """
    # Import plugins here to avoid circular imports
    from analysis_core.plugins.builtin.embedding import embedding_plugin
    from analysis_core.plugins.builtin.extraction import extraction_plugin
    from analysis_core.plugins.builtin.hierarchical_aggregation import hierarchical_aggregation_plugin
    from analysis_core.plugins.builtin.hierarchical_clustering import hierarchical_clustering_plugin
    from analysis_core.plugins.builtin.hierarchical_initial_labelling import hierarchical_initial_labelling_plugin
    from analysis_core.plugins.builtin.hierarchical_merge_labelling import hierarchical_merge_labelling_plugin
    from analysis_core.plugins.builtin.hierarchical_overview import hierarchical_overview_plugin
    from analysis_core.plugins.builtin.hierarchical_visualization import hierarchical_visualization_plugin

    plugins = [
        extraction_plugin,
        embedding_plugin,
        hierarchical_clustering_plugin,
        hierarchical_initial_labelling_plugin,
        hierarchical_merge_labelling_plugin,
        hierarchical_overview_plugin,
        hierarchical_aggregation_plugin,
        hierarchical_visualization_plugin,
    ]

    for plugin in plugins:
        registry.register(plugin)
