"""
Plugin registry for discovering and managing input plugins.
"""

import logging

from src.plugins.base import InputPlugin, PluginConfigError, PluginManifest

logger = logging.getLogger("uvicorn")


class PluginRegistry:
    """
    Central registry for input plugins.

    Plugins are registered by their manifest ID and can be discovered
    dynamically based on their availability.

    Plugin loading behavior:
    - Plugins are always registered to allow API to list available plugins
    - If a plugin is enabled but missing required settings, server fails on startup
    - If a plugin is not enabled, it's registered but not available for use
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

        If the plugin is explicitly enabled via environment variable but
        required settings are missing, raises PluginConfigError to fail startup.
        """
        manifest = plugin_class.manifest
        cls._plugins[manifest.id] = plugin_class

        # Check if plugin is enabled
        if manifest.is_enabled():
            # Plugin is enabled - validate settings are present
            is_valid, errors = manifest.validate_settings()
            if not is_valid:
                error_msg = f"Plugin '{manifest.id}' is enabled but missing required settings:\n" + "\n".join(
                    f"  - {e}" for e in errors
                )
                logger.error(error_msg)
                raise PluginConfigError(manifest.id, errors)
            logger.info(f"Registered and enabled input plugin: {manifest.id} (v{manifest.version})")
        else:
            logger.info(f"Registered input plugin (disabled): {manifest.id} (v{manifest.version})")

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
    Load all built-in plugins by auto-discovering modules in src.plugins package.

    This is called during application startup to register
    all available input plugins. Plugins are discovered automatically
    by scanning the plugins directory for Python modules.
    """
    import importlib
    import pkgutil

    from src import plugins

    # Modules to skip (not plugins)
    skip_modules = {"base", "registry", "__init__"}

    loaded = []
    for _, name, _ in pkgutil.iter_modules(plugins.__path__):
        if name in skip_modules:
            continue
        try:
            importlib.import_module(f"src.plugins.{name}")
            loaded.append(name)
        except ImportError as e:
            logger.warning(f"Failed to load plugin '{name}': {e}")

    if loaded:
        logger.info(f"Loaded built-in input plugins: {', '.join(loaded)}")
    else:
        logger.info("No built-in input plugins loaded")
