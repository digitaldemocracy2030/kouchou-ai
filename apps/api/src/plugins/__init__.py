"""
Input plugin system for kouchou-ai.

Plugins allow extending input sources (e.g., YouTube, Twitter) without modifying core code.
Each plugin declares its required settings, and the system validates them early.
"""

from src.plugins.base import InputPlugin, PluginManifest, PluginSetting
from src.plugins.registry import PluginRegistry

__all__ = ["InputPlugin", "PluginManifest", "PluginSetting", "PluginRegistry"]
