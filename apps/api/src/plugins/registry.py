"""
Plugin registry for discovering and managing input plugins.
"""

import logging

from src.plugins.base import InputPlugin, PluginManifest

logger = logging.getLogger("uvicorn")


class PluginRegistry:
    """
    Central registry for input plugins.

    Plugins are registered by their manifest ID and can be discovered
    dynamically based on their availability.
    """

    _plugins: dict[str, type[InputPlugin]] = {}
    _instances: dict[str, InputPlugin] = {}

    @classmethod
    def register(cls, plugin_class: type[InputPlugin]) -> type[InputPlugin]:
        """
        Register a plugin class.

        Can be used as a decorator:
            @PluginRegistry.register
            class MyPlugin(InputPlugin):
                ...
        """
        manifest = plugin_class.manifest
        cls._plugins[manifest.id] = plugin_class
        logger.info(f"Registered input plugin: {manifest.id} (v{manifest.version})")
        return plugin_class

    @classmethod
    def get_plugin(cls, plugin_id: str) -> InputPlugin | None:
        """
        Get a plugin instance by ID.

        Returns None if the plugin is not registered.
        Instances are cached for reuse.
        """
        if plugin_id not in cls._plugins:
            return None

        if plugin_id not in cls._instances:
            cls._instances[plugin_id] = cls._plugins[plugin_id]()

        return cls._instances[plugin_id]

    @classmethod
    def get_manifest(cls, plugin_id: str) -> PluginManifest | None:
        """Get a plugin's manifest by ID."""
        if plugin_id not in cls._plugins:
            return None
        return cls._plugins[plugin_id].manifest

    @classmethod
    def list_plugins(cls) -> list[PluginManifest]:
        """List all registered plugins."""
        return [p.manifest for p in cls._plugins.values()]

    @classmethod
    def list_available_plugins(cls) -> list[PluginManifest]:
        """List plugins that are properly configured and available."""
        return [p.manifest for p in cls._plugins.values() if p.manifest.is_available()]

    @classmethod
    def get_all_manifests(cls) -> list[dict]:
        """Get all plugin manifests as dictionaries for API response."""
        return [p.manifest.to_dict() for p in cls._plugins.values()]

    @classmethod
    def clear(cls) -> None:
        """Clear all registered plugins (for testing)."""
        cls._plugins.clear()
        cls._instances.clear()


def load_builtin_plugins() -> None:
    """
    Load all built-in plugins.

    This is called during application startup to register
    all available input plugins.
    """
    # Import plugins to trigger registration
    # Each plugin module uses @PluginRegistry.register decorator
    try:
        from src.plugins import youtube  # noqa: F401

        logger.info("Loaded built-in input plugins")
    except ImportError as e:
        logger.warning(f"Failed to load some plugins: {e}")
