"""
Decorator for creating function-based plugins.

This module provides a decorator that allows defining plugins as simple functions
instead of classes.
"""

from typing import Any, Callable

from analysis_core.plugin.interface import (
    AnalysisStepPlugin,
    PluginMetadata,
    StepContext,
    StepInputs,
    StepOutputs,
)

StepFunction = Callable[[StepContext, StepInputs, dict[str, Any]], StepOutputs]


class FunctionPlugin(AnalysisStepPlugin):
    """
    Plugin wrapper for function-based step implementations.

    This class wraps a function and its metadata to create a plugin
    that conforms to the AnalysisStepPlugin interface.
    """

    def __init__(
        self,
        func: StepFunction,
        plugin_metadata: PluginMetadata,
        validator: Callable[[dict[str, Any]], list[str]] | None = None,
    ):
        self._func = func
        self._metadata = plugin_metadata
        self._validator = validator

    @property
    def metadata(self) -> PluginMetadata:
        return self._metadata

    def run(
        self,
        ctx: StepContext,
        inputs: StepInputs,
        config: dict[str, Any],
    ) -> StepOutputs:
        return self._func(ctx, inputs, config)

    def validate_config(self, config: dict[str, Any]) -> list[str]:
        if self._validator:
            return self._validator(config)
        return []


def step_plugin(
    id: str,
    version: str,
    name: str = "",
    description: str = "",
    inputs: list[str] | None = None,
    outputs: list[str] | None = None,
    use_llm: bool = False,
    config_schema: dict[str, Any] | None = None,
    validator: Callable[[dict[str, Any]], list[str]] | None = None,
) -> Callable[[StepFunction], FunctionPlugin]:
    """
    Decorator for creating function-based plugins.

    This decorator transforms a function into a plugin that can be registered
    with the plugin registry.

    Args:
        id: Unique plugin identifier (e.g., "analysis.extraction")
        version: Plugin version in semver format
        name: Human-readable name (defaults to function name)
        description: Plugin description (defaults to function docstring)
        inputs: List of required input artifact IDs
        outputs: List of produced output artifact IDs
        use_llm: Whether this step uses LLM calls
        config_schema: JSON Schema for step configuration
        validator: Optional function to validate step configuration

    Returns:
        Decorator that transforms a function into a FunctionPlugin

    Example:
        @step_plugin(
            id="analysis.extraction",
            version="1.0.0",
            inputs=["comments"],
            outputs=["arguments", "relations"],
            use_llm=True,
        )
        def extraction(
            ctx: StepContext,
            inputs: StepInputs,
            config: dict[str, Any],
        ) -> StepOutputs:
            # Implementation here
            ...
    """

    def decorator(func: StepFunction) -> FunctionPlugin:
        plugin_metadata = PluginMetadata(
            id=id,
            version=version,
            name=name or func.__name__,
            description=description or (func.__doc__ or "").strip(),
            inputs=inputs or [],
            outputs=outputs or [],
            use_llm=use_llm,
            config_schema=config_schema,
        )

        # Create the plugin
        plugin = FunctionPlugin(func, plugin_metadata, validator)

        # Preserve function metadata on the plugin for introspection
        plugin.__name__ = func.__name__
        plugin.__doc__ = func.__doc__
        plugin.__module__ = func.__module__
        plugin.__wrapped__ = func

        return plugin

    return decorator
