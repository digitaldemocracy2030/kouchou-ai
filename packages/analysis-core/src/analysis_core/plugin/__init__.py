"""
Plugin system for analysis steps.

This module provides the infrastructure for creating, registering,
and executing analysis step plugins.

Example usage:

    from analysis_core.plugin import (
        step_plugin,
        StepContext,
        StepInputs,
        StepOutputs,
        get_registry,
    )

    # Define a plugin using the decorator
    @step_plugin(
        id="analysis.custom",
        version="1.0.0",
        inputs=["data"],
        outputs=["result"],
    )
    def custom_step(ctx, inputs, config):
        # Implementation
        return StepOutputs(artifacts={"result": ctx.output_dir / "result.csv"})

    # Register and use
    registry = get_registry()
    registry.register(custom_step)
"""

from analysis_core.plugin.decorator import FunctionPlugin, step_plugin
from analysis_core.plugin.interface import (
    AnalysisStepPlugin,
    PluginMetadata,
    StepContext,
    StepInputs,
    StepOutputs,
)
from analysis_core.plugin.loader import (
    LoadedPlugin,
    PluginLoadError,
    PluginManifest,
    discover_plugin_directories,
    load_all_plugins,
    load_manifest,
    load_plugin_from_directory,
    load_plugins_from_directory,
)
from analysis_core.plugin.registry import (
    PluginNotFoundError,
    PluginRegistry,
    get_registry,
    reset_registry,
)

__all__ = [
    # Interface
    "AnalysisStepPlugin",
    "PluginMetadata",
    "StepContext",
    "StepInputs",
    "StepOutputs",
    # Decorator
    "step_plugin",
    "FunctionPlugin",
    # Registry
    "PluginRegistry",
    "PluginNotFoundError",
    "get_registry",
    "reset_registry",
    # Loader
    "PluginLoadError",
    "PluginManifest",
    "LoadedPlugin",
    "load_manifest",
    "load_plugin_from_directory",
    "load_plugins_from_directory",
    "discover_plugin_directories",
    "load_all_plugins",
]
