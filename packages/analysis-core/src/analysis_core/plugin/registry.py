"""
Plugin registry for managing analysis step plugins.

This module provides a centralized registry for registering, discovering,
and retrieving analysis step plugins.
"""

from typing import Iterator

from analysis_core.plugin.interface import AnalysisStepPlugin, PluginMetadata


class PluginNotFoundError(Exception):
    """Raised when a requested plugin is not found in the registry."""

    pass


class PluginRegistry:
    """
    Registry for managing analysis step plugins.

    The registry maintains a collection of plugins indexed by their IDs.
    It supports registering new plugins, retrieving plugins by ID,
    and listing all registered plugins.

    Example:
        registry = PluginRegistry()
        registry.register(my_plugin)
        plugin = registry.get("analysis.extraction")
    """

    def __init__(self):
        self._plugins: dict[str, AnalysisStepPlugin] = {}
        self._builtin_registered = False

    def register(self, plugin: AnalysisStepPlugin) -> None:
        """
        Register a plugin.

        Args:
            plugin: Plugin instance to register

        Raises:
            ValueError: If a plugin with the same ID is already registered
        """
        plugin_id = plugin.id
        if plugin_id in self._plugins:
            raise ValueError(f"Plugin '{plugin_id}' is already registered")
        self._plugins[plugin_id] = plugin

    def register_or_replace(self, plugin: AnalysisStepPlugin) -> None:
        """
        Register a plugin, replacing any existing plugin with the same ID.

        Args:
            plugin: Plugin instance to register
        """
        self._plugins[plugin.id] = plugin

    def unregister(self, plugin_id: str) -> None:
        """
        Unregister a plugin by ID.

        Args:
            plugin_id: ID of the plugin to unregister

        Raises:
            PluginNotFoundError: If no plugin with the given ID is registered
        """
        if plugin_id not in self._plugins:
            raise PluginNotFoundError(f"Plugin '{plugin_id}' not found")
        del self._plugins[plugin_id]

    def get(self, plugin_id: str) -> AnalysisStepPlugin:
        """
        Get a plugin by ID.

        Args:
            plugin_id: ID of the plugin to retrieve

        Returns:
            The registered plugin

        Raises:
            PluginNotFoundError: If no plugin with the given ID is registered
        """
        if plugin_id not in self._plugins:
            raise PluginNotFoundError(f"Plugin '{plugin_id}' not found")
        return self._plugins[plugin_id]

    def get_or_none(self, plugin_id: str) -> AnalysisStepPlugin | None:
        """
        Get a plugin by ID, returning None if not found.

        Args:
            plugin_id: ID of the plugin to retrieve

        Returns:
            The registered plugin, or None if not found
        """
        return self._plugins.get(plugin_id)

    def has(self, plugin_id: str) -> bool:
        """
        Check if a plugin is registered.

        Args:
            plugin_id: ID of the plugin to check

        Returns:
            True if the plugin is registered, False otherwise
        """
        return plugin_id in self._plugins

    def list_plugins(self) -> list[str]:
        """
        List all registered plugin IDs.

        Returns:
            List of plugin IDs
        """
        return list(self._plugins.keys())

    def list_metadata(self) -> list[PluginMetadata]:
        """
        List metadata for all registered plugins.

        Returns:
            List of plugin metadata objects
        """
        return [plugin.metadata for plugin in self._plugins.values()]

    def __iter__(self) -> Iterator[AnalysisStepPlugin]:
        """Iterate over registered plugins."""
        return iter(self._plugins.values())

    def __len__(self) -> int:
        """Return the number of registered plugins."""
        return len(self._plugins)

    def __contains__(self, plugin_id: str) -> bool:
        """Check if a plugin ID is registered."""
        return plugin_id in self._plugins

    def register_builtin_plugins(self) -> None:
        """
        Register all built-in plugins.

        This method is idempotent - calling it multiple times has no effect
        after the first call.
        """
        if self._builtin_registered:
            return

        from analysis_core.plugins.builtin import register_all

        register_all(self)
        self._builtin_registered = True

    def clear(self) -> None:
        """Clear all registered plugins."""
        self._plugins.clear()
        self._builtin_registered = False


# Global registry instance
_global_registry: PluginRegistry | None = None


def get_registry() -> PluginRegistry:
    """
    Get the global plugin registry.

    Returns:
        The global PluginRegistry instance
    """
    global _global_registry
    if _global_registry is None:
        _global_registry = PluginRegistry()
    return _global_registry


def reset_registry() -> None:
    """
    Reset the global registry.

    This is primarily useful for testing.
    """
    global _global_registry
    _global_registry = None
