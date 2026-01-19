"""
Plugin loader for loading external plugins from directories.

This module provides functionality to load plugins from a directory structure
where each plugin is in its own subdirectory with a manifest.yaml file.

Directory structure:
    plugins/analysis/
    ├── my-custom-step/
    │   ├── manifest.yaml
    │   └── plugin.py
    ├── another-step/
    │   ├── manifest.yaml
    │   └── step.py

Example manifest.yaml:
    id: analysis.my-custom-step
    version: "1.0.0"
    name: "My Custom Step"
    description: "Custom analysis step"
    entry: plugin:my_step_plugin
    inputs:
      - comments
    outputs:
      - result
    use_llm: false

The `entry` field specifies the module and attribute name separated by a colon.
For example, `plugin:my_step_plugin` means load `my_step_plugin` from `plugin.py`.
"""

import importlib.util
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from analysis_core.plugin.interface import AnalysisStepPlugin
from analysis_core.plugin.registry import PluginRegistry

logger = logging.getLogger(__name__)


class PluginLoadError(Exception):
    """Error raised when a plugin fails to load."""

    def __init__(self, plugin_path: Path, message: str):
        self.plugin_path = plugin_path
        super().__init__(f"Failed to load plugin from {plugin_path}: {message}")


@dataclass
class PluginManifest:
    """Parsed plugin manifest."""

    id: str
    version: str
    name: str
    description: str
    entry: str
    inputs: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    use_llm: bool = False
    config_schema: dict[str, Any] | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PluginManifest":
        """Create a manifest from a dictionary."""
        return cls(
            id=data["id"],
            version=data["version"],
            name=data.get("name", data["id"]),
            description=data.get("description", ""),
            entry=data["entry"],
            inputs=data.get("inputs", []),
            outputs=data.get("outputs", []),
            use_llm=data.get("use_llm", False),
            config_schema=data.get("config_schema"),
        )


@dataclass
class LoadedPlugin:
    """Information about a loaded plugin."""

    plugin: AnalysisStepPlugin
    manifest: PluginManifest
    path: Path


def load_manifest(manifest_path: Path) -> PluginManifest:
    """
    Load a plugin manifest from a YAML file.

    Args:
        manifest_path: Path to the manifest.yaml file

    Returns:
        Parsed PluginManifest

    Raises:
        PluginLoadError: If the manifest is invalid or cannot be read
    """
    try:
        with open(manifest_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        if not isinstance(data, dict):
            raise PluginLoadError(manifest_path.parent, "Manifest must be a YAML object")

        required_fields = ["id", "version", "entry"]
        for field_name in required_fields:
            if field_name not in data:
                raise PluginLoadError(
                    manifest_path.parent,
                    f"Missing required field: {field_name}",
                )

        return PluginManifest.from_dict(data)
    except yaml.YAMLError as e:
        raise PluginLoadError(manifest_path.parent, f"Invalid YAML: {e}") from e
    except OSError as e:
        raise PluginLoadError(manifest_path.parent, f"Cannot read file: {e}") from e


def load_plugin_module(
    plugin_dir: Path,
    manifest: PluginManifest,
) -> AnalysisStepPlugin:
    """
    Load a plugin from a Python module.

    Args:
        plugin_dir: Directory containing the plugin
        manifest: Parsed manifest

    Returns:
        The loaded plugin instance

    Raises:
        PluginLoadError: If the plugin cannot be loaded
    """
    entry_parts = manifest.entry.split(":")
    if len(entry_parts) != 2:
        raise PluginLoadError(
            plugin_dir,
            f"Invalid entry format: {manifest.entry!r} (expected 'module:attribute')",
        )

    module_name, attr_name = entry_parts
    module_file = plugin_dir / f"{module_name}.py"

    if not module_file.exists():
        raise PluginLoadError(plugin_dir, f"Module file not found: {module_file}")

    try:
        full_module_name = f"analysis_core_external_plugin_{manifest.id.replace('.', '_')}"

        spec = importlib.util.spec_from_file_location(full_module_name, module_file)
        if spec is None or spec.loader is None:
            raise PluginLoadError(plugin_dir, f"Cannot create module spec for {module_file}")

        module = importlib.util.module_from_spec(spec)
        sys.modules[full_module_name] = module
        spec.loader.exec_module(module)

        if not hasattr(module, attr_name):
            raise PluginLoadError(
                plugin_dir,
                f"Attribute {attr_name!r} not found in module {module_name}",
            )

        plugin = getattr(module, attr_name)

        if not isinstance(plugin, AnalysisStepPlugin):
            raise PluginLoadError(
                plugin_dir,
                f"Attribute {attr_name!r} is not an AnalysisStepPlugin (got {type(plugin).__name__})",
            )

        return plugin

    except ImportError as e:
        raise PluginLoadError(plugin_dir, f"Import error: {e}") from e
    except Exception as e:
        if isinstance(e, PluginLoadError):
            raise
        raise PluginLoadError(plugin_dir, f"Failed to load module: {e}") from e


def load_plugin_from_directory(plugin_dir: Path) -> LoadedPlugin:
    """
    Load a single plugin from a directory.

    Args:
        plugin_dir: Directory containing the plugin

    Returns:
        LoadedPlugin with the plugin instance and metadata

    Raises:
        PluginLoadError: If the plugin cannot be loaded
    """
    manifest_path = plugin_dir / "manifest.yaml"
    if not manifest_path.exists():
        raise PluginLoadError(plugin_dir, "manifest.yaml not found")

    manifest = load_manifest(manifest_path)
    plugin = load_plugin_module(plugin_dir, manifest)

    return LoadedPlugin(plugin=plugin, manifest=manifest, path=plugin_dir)


def load_plugins_from_directory(
    directory: Path,
    registry: PluginRegistry | None = None,
    *,
    ignore_errors: bool = False,
) -> list[LoadedPlugin]:
    """
    Load all plugins from a directory.

    Args:
        directory: Directory containing plugin subdirectories
        registry: Optional registry to register loaded plugins
        ignore_errors: If True, continue loading other plugins when one fails

    Returns:
        List of successfully loaded plugins

    Raises:
        PluginLoadError: If ignore_errors is False and a plugin fails to load
    """
    if not directory.exists():
        logger.debug(f"Plugin directory does not exist: {directory}")
        return []

    if not directory.is_dir():
        raise PluginLoadError(directory, "Not a directory")

    loaded: list[LoadedPlugin] = []
    errors: list[tuple[Path, Exception]] = []

    for item in sorted(directory.iterdir()):
        if not item.is_dir():
            continue

        manifest_path = item / "manifest.yaml"
        if not manifest_path.exists():
            logger.debug(f"Skipping {item.name}: no manifest.yaml")
            continue

        try:
            result = load_plugin_from_directory(item)
            loaded.append(result)

            if registry is not None:
                registry.register_or_replace(result.plugin)
                logger.info(f"Loaded plugin: {result.manifest.id} v{result.manifest.version}")

        except PluginLoadError as e:
            if ignore_errors:
                logger.warning(f"Failed to load plugin from {item}: {e}")
                errors.append((item, e))
            else:
                raise

    return loaded


def discover_plugin_directories(
    base_paths: list[Path] | None = None,
) -> list[Path]:
    """
    Discover plugin directories in common locations.

    Searches for plugin directories in:
    1. Paths provided in base_paths
    2. ./plugins/analysis/ (relative to current working directory)
    3. ANALYSIS_PLUGINS_PATH environment variable

    Args:
        base_paths: Additional paths to search

    Returns:
        List of existing plugin directories
    """
    import os

    directories: list[Path] = []

    if base_paths:
        directories.extend(base_paths)

    cwd_plugins = Path.cwd() / "plugins" / "analysis"
    if cwd_plugins.exists():
        directories.append(cwd_plugins)

    env_path = os.environ.get("ANALYSIS_PLUGINS_PATH")
    if env_path:
        for path_str in env_path.split(os.pathsep):
            path = Path(path_str)
            if path.exists():
                directories.append(path)

    unique_dirs = []
    seen = set()
    for d in directories:
        resolved = d.resolve()
        if resolved not in seen:
            seen.add(resolved)
            unique_dirs.append(d)

    return unique_dirs


def load_all_plugins(
    registry: PluginRegistry | None = None,
    plugin_paths: list[Path] | None = None,
    *,
    include_builtin: bool = True,
    ignore_errors: bool = True,
) -> list[LoadedPlugin]:
    """
    Load all available plugins (builtin and external).

    Args:
        registry: Registry to register plugins to. If None, uses global registry.
        plugin_paths: Paths to search for external plugins
        include_builtin: Whether to register builtin plugins
        ignore_errors: Whether to continue on plugin load errors

    Returns:
        List of loaded external plugins
    """
    from analysis_core.plugin.registry import get_registry

    if registry is None:
        registry = get_registry()

    if include_builtin:
        registry.register_builtin_plugins()

    directories = discover_plugin_directories(plugin_paths)
    loaded: list[LoadedPlugin] = []

    for directory in directories:
        plugins = load_plugins_from_directory(
            directory,
            registry,
            ignore_errors=ignore_errors,
        )
        loaded.extend(plugins)

    return loaded
