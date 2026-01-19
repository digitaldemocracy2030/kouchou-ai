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

from analysis_core.plugin.interface import (
    AnalysisStepPlugin,
    PluginMetadata,
    StepContext,
    StepInputs,
    StepOutputs,
)
from analysis_core.plugin.decorator import step_plugin, FunctionPlugin
from analysis_core.plugin.registry import (
    PluginRegistry,
    PluginNotFoundError,
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
]
