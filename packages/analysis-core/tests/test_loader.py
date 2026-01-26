"""Tests for plugin loader functionality."""

import tempfile
from pathlib import Path

import pytest

from analysis_core.plugin import (
    PluginLoadError,
    PluginManifest,
    PluginRegistry,
    StepContext,
    StepInputs,
    StepOutputs,
    load_manifest,
    load_plugin_from_directory,
    load_plugins_from_directory,
    step_plugin,
)


@pytest.fixture
def temp_plugin_dir():
    """Create a temporary directory for plugin testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def valid_manifest_dict():
    """Valid manifest data."""
    return {
        "id": "test.sample-plugin",
        "version": "1.0.0",
        "name": "Sample Plugin",
        "description": "A test plugin",
        "entry": "plugin:sample_plugin",
        "inputs": ["data"],
        "outputs": ["result"],
        "use_llm": False,
    }


class TestPluginManifest:
    """Tests for PluginManifest."""

    def test_from_dict_minimal(self):
        """Test creating manifest with minimal required fields."""
        data = {
            "id": "test.minimal",
            "version": "1.0.0",
            "entry": "plugin:my_plugin",
        }
        manifest = PluginManifest.from_dict(data)
        assert manifest.id == "test.minimal"
        assert manifest.version == "1.0.0"
        assert manifest.entry == "plugin:my_plugin"
        assert manifest.name == "test.minimal"  # Falls back to id
        assert manifest.description == ""
        assert manifest.inputs == []
        assert manifest.outputs == []
        assert manifest.use_llm is False

    def test_from_dict_full(self, valid_manifest_dict):
        """Test creating manifest with all fields."""
        manifest = PluginManifest.from_dict(valid_manifest_dict)
        assert manifest.id == "test.sample-plugin"
        assert manifest.version == "1.0.0"
        assert manifest.name == "Sample Plugin"
        assert manifest.description == "A test plugin"
        assert manifest.entry == "plugin:sample_plugin"
        assert manifest.inputs == ["data"]
        assert manifest.outputs == ["result"]
        assert manifest.use_llm is False


class TestLoadManifest:
    """Tests for load_manifest function."""

    def test_load_valid_manifest(self, temp_plugin_dir, valid_manifest_dict):
        """Test loading a valid manifest file."""
        import yaml

        manifest_path = temp_plugin_dir / "manifest.yaml"
        with open(manifest_path, "w") as f:
            yaml.dump(valid_manifest_dict, f)

        manifest = load_manifest(manifest_path)
        assert manifest.id == "test.sample-plugin"
        assert manifest.version == "1.0.0"

    def test_load_missing_file(self, temp_plugin_dir):
        """Test loading a non-existent manifest file."""
        manifest_path = temp_plugin_dir / "manifest.yaml"
        with pytest.raises(PluginLoadError) as exc_info:
            load_manifest(manifest_path)
        assert "Cannot read file" in str(exc_info.value)

    def test_load_invalid_yaml(self, temp_plugin_dir):
        """Test loading an invalid YAML file."""
        manifest_path = temp_plugin_dir / "manifest.yaml"
        with open(manifest_path, "w") as f:
            f.write("invalid: yaml: content: [")

        with pytest.raises(PluginLoadError) as exc_info:
            load_manifest(manifest_path)
        assert "Invalid YAML" in str(exc_info.value)

    def test_load_missing_required_field(self, temp_plugin_dir):
        """Test loading a manifest missing required fields."""
        import yaml

        manifest_path = temp_plugin_dir / "manifest.yaml"
        with open(manifest_path, "w") as f:
            yaml.dump({"id": "test.incomplete", "version": "1.0.0"}, f)

        with pytest.raises(PluginLoadError) as exc_info:
            load_manifest(manifest_path)
        assert "Missing required field: entry" in str(exc_info.value)


class TestLoadPluginFromDirectory:
    """Tests for load_plugin_from_directory function."""

    def test_load_valid_plugin(self, temp_plugin_dir):
        """Test loading a valid plugin."""
        import yaml

        manifest = {
            "id": "test.example",
            "version": "1.0.0",
            "entry": "plugin:example_plugin",
            "inputs": [],
            "outputs": ["result"],
        }
        with open(temp_plugin_dir / "manifest.yaml", "w") as f:
            yaml.dump(manifest, f)

        plugin_code = """
from analysis_core.plugin import step_plugin, StepContext, StepInputs, StepOutputs

@step_plugin(
    id="test.example",
    version="1.0.0",
    inputs=[],
    outputs=["result"],
)
def example_plugin(ctx: StepContext, inputs: StepInputs, config: dict) -> StepOutputs:
    return StepOutputs(artifacts={"result": ctx.output_dir / "result.txt"})
"""
        with open(temp_plugin_dir / "plugin.py", "w") as f:
            f.write(plugin_code)

        result = load_plugin_from_directory(temp_plugin_dir)
        assert result.manifest.id == "test.example"
        assert result.plugin.id == "test.example"
        assert result.path == temp_plugin_dir

    def test_load_missing_manifest(self, temp_plugin_dir):
        """Test loading from a directory without manifest."""
        with pytest.raises(PluginLoadError) as exc_info:
            load_plugin_from_directory(temp_plugin_dir)
        assert "manifest.yaml not found" in str(exc_info.value)

    def test_load_missing_module(self, temp_plugin_dir):
        """Test loading with missing module file."""
        import yaml

        manifest = {
            "id": "test.missing",
            "version": "1.0.0",
            "entry": "missing_module:plugin",
        }
        with open(temp_plugin_dir / "manifest.yaml", "w") as f:
            yaml.dump(manifest, f)

        with pytest.raises(PluginLoadError) as exc_info:
            load_plugin_from_directory(temp_plugin_dir)
        assert "Module file not found" in str(exc_info.value)

    def test_load_invalid_entry_format(self, temp_plugin_dir):
        """Test loading with invalid entry format."""
        import yaml

        manifest = {
            "id": "test.invalid-entry",
            "version": "1.0.0",
            "entry": "no_colon_separator",
        }
        with open(temp_plugin_dir / "manifest.yaml", "w") as f:
            yaml.dump(manifest, f)

        with pytest.raises(PluginLoadError) as exc_info:
            load_plugin_from_directory(temp_plugin_dir)
        assert "Invalid entry format" in str(exc_info.value)


class TestLoadPluginsFromDirectory:
    """Tests for load_plugins_from_directory function."""

    def test_load_multiple_plugins(self, temp_plugin_dir):
        """Test loading multiple plugins from a directory."""
        import yaml

        for name in ["plugin-a", "plugin-b"]:
            plugin_dir = temp_plugin_dir / name
            plugin_dir.mkdir()

            manifest = {
                "id": f"test.{name}",
                "version": "1.0.0",
                "entry": "plugin:the_plugin",
            }
            with open(plugin_dir / "manifest.yaml", "w") as f:
                yaml.dump(manifest, f)

            plugin_code = f"""
from analysis_core.plugin import step_plugin, StepContext, StepInputs, StepOutputs

@step_plugin(
    id="test.{name}",
    version="1.0.0",
)
def the_plugin(ctx: StepContext, inputs: StepInputs, config: dict) -> StepOutputs:
    return StepOutputs()
"""
            with open(plugin_dir / "plugin.py", "w") as f:
                f.write(plugin_code)

        registry = PluginRegistry()
        loaded = load_plugins_from_directory(temp_plugin_dir, registry)

        assert len(loaded) == 2
        assert registry.has("test.plugin-a")
        assert registry.has("test.plugin-b")

    def test_load_empty_directory(self, temp_plugin_dir):
        """Test loading from an empty directory."""
        loaded = load_plugins_from_directory(temp_plugin_dir)
        assert loaded == []

    def test_load_nonexistent_directory(self, temp_plugin_dir):
        """Test loading from a non-existent directory."""
        nonexistent = temp_plugin_dir / "nonexistent"
        loaded = load_plugins_from_directory(nonexistent)
        assert loaded == []

    def test_skip_non_directories(self, temp_plugin_dir):
        """Test that regular files are skipped."""
        (temp_plugin_dir / "not_a_plugin.txt").write_text("hello")
        loaded = load_plugins_from_directory(temp_plugin_dir)
        assert loaded == []

    def test_skip_directories_without_manifest(self, temp_plugin_dir):
        """Test that directories without manifest.yaml are skipped."""
        (temp_plugin_dir / "not-a-plugin").mkdir()
        loaded = load_plugins_from_directory(temp_plugin_dir)
        assert loaded == []

    def test_ignore_errors(self, temp_plugin_dir):
        """Test ignore_errors flag."""
        import yaml

        # Create a valid plugin
        valid_dir = temp_plugin_dir / "valid"
        valid_dir.mkdir()
        with open(valid_dir / "manifest.yaml", "w") as f:
            yaml.dump({"id": "test.valid", "version": "1.0.0", "entry": "plugin:p"}, f)
        valid_code = """
from analysis_core.plugin import step_plugin, StepContext, StepInputs, StepOutputs

@step_plugin(id="test.valid", version="1.0.0")
def p(ctx: StepContext, inputs: StepInputs, config: dict) -> StepOutputs:
    return StepOutputs()
"""
        (valid_dir / "plugin.py").write_text(valid_code)

        # Create an invalid plugin (missing module)
        invalid_dir = temp_plugin_dir / "invalid"
        invalid_dir.mkdir()
        with open(invalid_dir / "manifest.yaml", "w") as f:
            yaml.dump({"id": "test.invalid", "version": "1.0.0", "entry": "missing:p"}, f)

        # With ignore_errors=True, should load valid and skip invalid
        loaded = load_plugins_from_directory(temp_plugin_dir, ignore_errors=True)
        assert len(loaded) == 1
        assert loaded[0].manifest.id == "test.valid"

        # With ignore_errors=False, should raise
        with pytest.raises(PluginLoadError):
            load_plugins_from_directory(temp_plugin_dir, ignore_errors=False)
