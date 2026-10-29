"""
Built-in analysis step plugins.

This module registers the standard analysis steps as plugins.
"""

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from analysis_core.plugin.registry import PluginRegistry


def register_all(registry: "PluginRegistry") -> None:
    """
    Register all built-in plugins with the registry.

    This function registers the standard analysis steps:
    - analysis.extraction
    - analysis.opinion_classification
    - analysis.opinion_stance
    - analysis.embedding
    - analysis.opinion_novelty
    - analysis.hierarchical_clustering
    - analysis.llm_grouping
    - analysis.hierarchical_initial_labelling
    - analysis.hierarchical_merge_labelling
    - analysis.hierarchical_overview
    - analysis.hierarchical_aggregation
    - analysis.hierarchical_visualization

    A plugin already registered with the same ID (e.g. an external plugin loaded
    by ``load_plugins_from_directory`` to replace a built-in step) is kept, so
    loading external plugins before ``register_builtin_plugins`` works the same
    as loading them after it.

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
    from analysis_core.plugins.builtin.llm_grouping import llm_grouping_plugin
    from analysis_core.plugins.builtin.opinion_classification import opinion_classification_plugin
    from analysis_core.plugins.builtin.opinion_novelty import opinion_novelty_plugin
    from analysis_core.plugins.builtin.opinion_stance import opinion_stance_plugin

    plugins = [
        extraction_plugin,
        opinion_classification_plugin,
        opinion_stance_plugin,
        embedding_plugin,
        opinion_novelty_plugin,
        hierarchical_clustering_plugin,
        llm_grouping_plugin,
        hierarchical_initial_labelling_plugin,
        hierarchical_merge_labelling_plugin,
        hierarchical_overview_plugin,
        hierarchical_aggregation_plugin,
        hierarchical_visualization_plugin,
    ]

    for plugin in plugins:
        if plugin.id in registry:
            logging.getLogger(__name__).info(
                "Keeping already registered plugin '%s' instead of the built-in one", plugin.id
            )
            continue
        registry.register(plugin)
