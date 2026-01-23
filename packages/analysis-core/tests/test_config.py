"""Tests for configuration management."""

import json
import tempfile
from pathlib import Path

import pytest

from analysis_core.config import PipelineConfig, load_config, save_config


class TestPipelineConfig:
    """Tests for PipelineConfig class."""

    def test_from_json(self, tmp_path: Path) -> None:
        """Test loading config from JSON file."""
        config_data = {
            "input": "test_input.csv",
            "output_dir": "test_output",
            "question": "What are people discussing?",
            "intro": "Test intro",
            "model": "gpt-4o-mini",
            "provider": "openai",
        }
        config_file = tmp_path / "config.json"
        with open(config_file, "w") as f:
            json.dump(config_data, f)

        config = PipelineConfig.from_json(config_file)

        assert config.input_path == Path("test_input.csv")
        assert config.output_dir == Path("test_output")
        assert config.question == "What are people discussing?"
        assert config.model == "gpt-4o-mini"

    def test_to_dict(self) -> None:
        """Test converting config to dictionary."""
        config = PipelineConfig(
            input_path=Path("input.csv"),
            output_dir=Path("output"),
            question="Test question",
            model="gpt-4",
        )

        result = config.to_dict()

        assert result["input"] == "input.csv"
        assert result["output_dir"] == "output"
        assert result["question"] == "Test question"
        assert result["model"] == "gpt-4"


class TestLoadSaveConfig:
    """Tests for load_config and save_config functions."""

    def test_load_config(self, tmp_path: Path) -> None:
        """Test loading legacy config file."""
        config_data = {"key": "value", "nested": {"a": 1}}
        config_file = tmp_path / "config.json"
        with open(config_file, "w") as f:
            json.dump(config_data, f)

        result = load_config(config_file)

        assert result == config_data

    def test_save_config(self, tmp_path: Path) -> None:
        """Test saving config to file."""
        config_data = {"key": "value", "日本語": "テスト"}
        config_file = tmp_path / "config.json"

        save_config(config_data, config_file)

        with open(config_file, "r", encoding="utf-8") as f:
            result = json.load(f)
        assert result == config_data
