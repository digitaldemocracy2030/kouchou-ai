"""Test cases for plugin registry and base classes."""

import os
from unittest.mock import patch

import pandas as pd
import pytest

from src.plugins.base import InputPlugin, PluginConfigError, PluginManifest, PluginSetting, SettingType
from src.plugins.registry import PluginRegistry


class TestPluginSetting:
    """Test cases for PluginSetting class."""

    def test_setting_get_value_from_env(self):
        """環境変数から設定値を取得できる"""
        setting = PluginSetting(
            key="TEST_API_KEY",
            label="Test API Key",
            description="Test description",
            setting_type=SettingType.STRING,
            required=True,
        )

        with patch.dict(os.environ, {"TEST_API_KEY": "test-value"}):
            assert setting.get_value() == "test-value"
            assert setting.is_configured() is True

    def test_setting_get_value_missing(self):
        """環境変数が設定されていない場合はNoneを返す"""
        setting = PluginSetting(
            key="MISSING_KEY",
            label="Missing Key",
            description="Test description",
            setting_type=SettingType.STRING,
            required=True,
        )

        with patch.dict(os.environ, {}, clear=True):
            # MISSING_KEYが確実に存在しないことを確認
            os.environ.pop("MISSING_KEY", None)
            assert setting.get_value() is None
            assert setting.is_configured() is False

    def test_setting_get_value_with_default(self):
        """デフォルト値が設定されている場合はそれを返す"""
        setting = PluginSetting(
            key="OPTIONAL_KEY",
            label="Optional Key",
            description="Test description",
            setting_type=SettingType.STRING,
            required=False,
            default="default-value",
        )

        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("OPTIONAL_KEY", None)
            assert setting.get_value() == "default-value"
            assert setting.is_configured() is True  # required=Falseなので常にTrue

    def test_setting_integer_conversion(self):
        """整数型の設定値が正しく変換される"""
        setting = PluginSetting(
            key="INT_KEY",
            label="Integer Key",
            description="Test description",
            setting_type=SettingType.INTEGER,
            required=True,
        )

        with patch.dict(os.environ, {"INT_KEY": "42"}):
            assert setting.get_value() == 42

    def test_setting_boolean_conversion(self):
        """真偽値型の設定値が正しく変換される"""
        setting = PluginSetting(
            key="BOOL_KEY",
            label="Boolean Key",
            description="Test description",
            setting_type=SettingType.BOOLEAN,
            required=True,
        )

        with patch.dict(os.environ, {"BOOL_KEY": "true"}):
            assert setting.get_value() is True

        with patch.dict(os.environ, {"BOOL_KEY": "false"}):
            assert setting.get_value() is False


class TestPluginManifest:
    """Test cases for PluginManifest class."""

    def test_manifest_validate_settings_all_configured(self):
        """全ての必須設定が構成されている場合はバリデーション成功"""
        manifest = PluginManifest(
            id="test-plugin",
            name="Test Plugin",
            description="Test description",
            settings=[
                PluginSetting(
                    key="TEST_KEY",
                    label="Test Key",
                    description="Test description",
                    required=True,
                ),
            ],
        )

        with patch.dict(os.environ, {"TEST_KEY": "value"}):
            is_valid, errors = manifest.validate_settings()
            assert is_valid is True
            assert len(errors) == 0

    def test_manifest_validate_settings_missing(self):
        """必須設定が欠けている場合はバリデーション失敗"""
        manifest = PluginManifest(
            id="test-plugin",
            name="Test Plugin",
            description="Test description",
            settings=[
                PluginSetting(
                    key="MISSING_KEY",
                    label="Missing Key",
                    description="Test description",
                    required=True,
                ),
            ],
        )

        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("MISSING_KEY", None)
            is_valid, errors = manifest.validate_settings()
            assert is_valid is False
            assert len(errors) == 1
            assert "MISSING_KEY" in errors[0]

    def test_manifest_to_dict(self):
        """マニフェストを辞書に変換できる"""
        manifest = PluginManifest(
            id="test-plugin",
            name="Test Plugin",
            description="Test description",
            version="1.0.0",
            icon="test-icon",
            enabled_by_default=False,
            settings=[
                PluginSetting(
                    key="TEST_KEY",
                    label="Test Key",
                    description="Key description",
                    setting_type=SettingType.SECRET,
                    required=True,
                ),
            ],
        )

        with patch.dict(os.environ, {"TEST_KEY": "value", "ENABLE_TEST-PLUGIN_INPUT_PLUGIN": "true"}):
            result = manifest.to_dict()

        assert result["id"] == "test-plugin"
        assert result["name"] == "Test Plugin"
        assert result["version"] == "1.0.0"
        assert result["icon"] == "test-icon"
        assert result["enabledByDefault"] is False
        assert result["isAvailable"] is True
        assert len(result["settings"]) == 1
        assert result["settings"][0]["key"] == "TEST_KEY"
        assert result["settings"][0]["type"] == "secret"


class TestPluginRegistry:
    """Test cases for PluginRegistry class."""

    def setup_method(self):
        """各テストの前にレジストリをクリア"""
        PluginRegistry.clear()

    def test_register_plugin(self):
        """プラグインを登録できる"""

        class TestPlugin(InputPlugin):
            manifest = PluginManifest(
                id="test-plugin",
                name="Test Plugin",
                description="Test description",
            )

            def fetch_data(self, source, **options):
                return pd.DataFrame()

        PluginRegistry.register(TestPlugin)

        assert "test-plugin" in [m.id for m in PluginRegistry.list_plugins()]

    def test_get_plugin(self):
        """登録済みプラグインのインスタンスを取得できる"""

        class TestPlugin(InputPlugin):
            manifest = PluginManifest(
                id="test-plugin",
                name="Test Plugin",
                description="Test description",
            )

            def fetch_data(self, source, **options):
                return pd.DataFrame()

        PluginRegistry.register(TestPlugin)

        plugin = PluginRegistry.get_plugin("test-plugin")
        assert plugin is not None
        assert isinstance(plugin, TestPlugin)

    def test_get_plugin_not_found(self):
        """存在しないプラグインはNoneを返す"""
        plugin = PluginRegistry.get_plugin("nonexistent")
        assert plugin is None

    def test_list_available_plugins(self):
        """利用可能なプラグインのみをリストできる"""

        class AvailablePlugin(InputPlugin):
            manifest = PluginManifest(
                id="available-plugin",
                name="Available Plugin",
                description="Test description",
                settings=[],  # 設定不要
            )

            def fetch_data(self, source, **options):
                return pd.DataFrame()

        class UnavailablePlugin(InputPlugin):
            manifest = PluginManifest(
                id="unavailable-plugin",
                name="Unavailable Plugin",
                description="Test description",
                settings=[
                    PluginSetting(
                        key="MISSING_KEY_FOR_TEST",
                        label="Missing Key",
                        description="Test description",
                        required=True,
                    ),
                ],
            )

            def fetch_data(self, source, **options):
                return pd.DataFrame()

        PluginRegistry.register(AvailablePlugin)
        PluginRegistry.register(UnavailablePlugin)

        with patch.dict(os.environ, {"ENABLE_AVAILABLE-PLUGIN_INPUT_PLUGIN": "true"}, clear=True):
            os.environ.pop("MISSING_KEY_FOR_TEST", None)
            available = PluginRegistry.list_available_plugins()

        assert len(available) == 1
        assert available[0].id == "available-plugin"


class TestInputPlugin:
    """Test cases for InputPlugin base class."""

    def test_ensure_configured_raises_on_missing_settings(self):
        """設定が不足している場合はPluginConfigErrorを送出"""

        class TestPlugin(InputPlugin):
            manifest = PluginManifest(
                id="test-plugin",
                name="Test Plugin",
                description="Test description",
                settings=[
                    PluginSetting(
                        key="REQUIRED_KEY_TEST",
                        label="Required Key",
                        description="Test description",
                        required=True,
                    ),
                ],
            )

            def fetch_data(self, source, **options):
                return pd.DataFrame()

        plugin = TestPlugin()

        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("REQUIRED_KEY_TEST", None)
            with pytest.raises(PluginConfigError) as exc_info:
                plugin.ensure_configured()

        assert "test-plugin" in str(exc_info.value)
        assert "REQUIRED_KEY_TEST" in str(exc_info.value)

    def test_validate_source_default_implementation(self):
        """デフォルトのvalidate_sourceは常にTrueを返す"""

        class TestPlugin(InputPlugin):
            manifest = PluginManifest(
                id="test-plugin",
                name="Test Plugin",
                description="Test description",
            )

            def fetch_data(self, source, **options):
                return pd.DataFrame()

        plugin = TestPlugin()
        is_valid, error = plugin.validate_source("any-source")

        assert is_valid is True
        assert error is None
