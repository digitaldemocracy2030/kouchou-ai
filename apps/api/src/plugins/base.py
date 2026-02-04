"""
Base classes for input plugins.

Each plugin must:
1. Define a manifest with required settings
2. Implement fetch_data() to retrieve comments from the source
3. Optionally implement validate_url() for URL-based sources
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

import pandas as pd

from src.config import settings


class SettingType(StrEnum):
    """Type of plugin setting."""

    STRING = "string"
    SECRET = "secret"  # Will be masked in UI
    INTEGER = "integer"
    BOOLEAN = "boolean"
    URL = "url"


@dataclass
class PluginSetting:
    """
    Declares a setting required by a plugin.

    Attributes:
        key: Environment variable name (e.g., "YOUTUBE_API_KEY")
        label: Human-readable label for UI
        description: Help text for the setting
        setting_type: Type of the setting value
        required: Whether the setting must be present
        default: Default value if not required
    """

    key: str
    label: str
    description: str
    setting_type: SettingType = SettingType.STRING
    required: bool = True
    default: Any = None

    def get_value(self) -> Any:
        """Get the setting value from environment."""
        import os

        value = os.environ.get(self.key, self.default)
        if value is None and self.required:
            return None

        if value is not None:
            if self.setting_type == SettingType.INTEGER:
                return int(value)
            elif self.setting_type == SettingType.BOOLEAN:
                return value.lower() in ("true", "1", "yes")

        return value

    def is_configured(self) -> bool:
        """Check if the setting is properly configured."""
        if not self.required:
            return True
        value = self.get_value()
        return value is not None and value != ""


@dataclass
class PluginManifest:
    """
    Plugin manifest declaring metadata and requirements.

    Attributes:
        id: Unique plugin identifier (e.g., "youtube", "twitter")
        name: Human-readable name
        description: Description shown in UI
        version: Plugin version (semver)
        settings: List of required settings
        enabled_by_default: Whether plugin is enabled without explicit configuration
        icon: Optional icon identifier for UI
        placeholder: Placeholder text for URL input field
    """

    id: str
    name: str
    description: str
    version: str = "1.0.0"
    settings: list[PluginSetting] = field(default_factory=list)
    enabled_by_default: bool = False
    icon: str | None = None
    placeholder: str = "URLを入力してください"

    def get_enable_env_var(self) -> str:
        """Get the environment variable name for enabling this plugin."""
        return f"ENABLE_{self.id.upper()}_INPUT_PLUGIN"

    def is_enabled(self) -> bool:
        """
        Check if the plugin is explicitly enabled via environment variable.

        Returns True only if ENABLE_{PLUGIN_ID}_INPUT_PLUGIN=true
        """
        import os

        env_var = self.get_enable_env_var()
        value = os.environ.get(env_var, "").lower()
        return value in ("true", "1", "yes")

    def validate_settings(self) -> tuple[bool, list[str]]:
        """
        Validate all required settings are configured.

        Returns:
            Tuple of (is_valid, list of error messages)
        """
        errors = []
        for setting in self.settings:
            if setting.required and not setting.is_configured():
                errors.append(f"Missing required setting: {setting.key} ({setting.label})")
        return len(errors) == 0, errors

    def is_available(self) -> bool:
        """
        Check if the plugin is available for use.

        A plugin is available only if:
        1. It is explicitly enabled via ENABLE_{PLUGIN_ID}_INPUT_PLUGIN=true
        2. All required settings are configured
        """
        if not self.is_enabled():
            return False
        is_valid, _ = self.validate_settings()
        return is_valid

    def to_dict(self) -> dict:
        """Convert manifest to dictionary for API response."""
        is_enabled = self.is_enabled()
        is_settings_valid, settings_errors = self.validate_settings()

        # Build missing settings messages
        missing_settings = []
        if not is_enabled:
            missing_settings.append(f"環境変数 {self.get_enable_env_var()}=true が必要です")
        missing_settings.extend(settings_errors)

        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "icon": self.icon,
            "placeholder": self.placeholder,
            "enabledByDefault": self.enabled_by_default,
            "isEnabled": is_enabled,
            "isAvailable": is_enabled and is_settings_valid,
            "missingSettings": missing_settings,
            "settings": [
                {
                    "key": s.key,
                    "label": s.label,
                    "description": s.description,
                    "type": s.setting_type.value,
                    "required": s.required,
                    "isConfigured": s.is_configured(),
                }
                for s in self.settings
            ],
        }


class InputPlugin(ABC):
    """
    Base class for input plugins.

    Subclasses must implement:
    - manifest: Class attribute defining plugin metadata
    - fetch_data(): Method to retrieve data from the source
    """

    manifest: PluginManifest

    @abstractmethod
    def fetch_data(self, source: str, **options: Any) -> pd.DataFrame:
        """
        Fetch data from the source.

        Args:
            source: URL or identifier for the data source
            **options: Additional options (e.g., max_results)

        Returns:
            DataFrame with columns: comment-id, comment-body, source, url
            Plus any optional attribute columns.

        Raises:
            ValueError: If source is invalid
            PluginConfigError: If required settings are missing
        """
        pass

    def validate_source(self, source: str) -> tuple[bool, str | None]:
        """
        Validate the source identifier/URL.

        Args:
            source: URL or identifier to validate

        Returns:
            Tuple of (is_valid, error_message or None)
        """
        return True, None

    def save_to_csv(self, df: pd.DataFrame, file_name: str) -> Path:
        """
        Save DataFrame to CSV in the input directory.

        Args:
            df: DataFrame to save
            file_name: Name for the CSV file (without extension)

        Returns:
            Path to the saved file
        """
        input_path = settings.INPUT_DIR / f"{file_name}.csv"
        df.to_csv(input_path, index=False)
        return input_path

    def ensure_configured(self) -> None:
        """
        Ensure all required settings are configured.

        Raises:
            PluginConfigError: If any required setting is missing
        """
        is_valid, errors = self.manifest.validate_settings()
        if not is_valid:
            raise PluginConfigError(self.manifest.id, errors)


class PluginConfigError(Exception):
    """Raised when plugin configuration is invalid."""

    def __init__(self, plugin_id: str, errors: list[str]):
        self.plugin_id = plugin_id
        self.errors = errors
        super().__init__(f"Plugin '{plugin_id}' configuration error: {'; '.join(errors)}")
