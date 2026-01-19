"""Tests for default prompts functionality."""

import json
from pathlib import Path

import pytest

from analysis_core.prompts import (
    DEFAULT_PROMPTS,
    EXTRACTION_PROMPT,
    INITIAL_LABELLING_PROMPT,
    MERGE_LABELLING_PROMPT,
    OVERVIEW_PROMPT,
    get_default_prompt,
)


class TestDefaultPrompts:
    """Tests for default prompt definitions."""

    def test_extraction_prompt_exists(self):
        """Test that extraction prompt is defined."""
        assert EXTRACTION_PROMPT is not None
        assert len(EXTRACTION_PROMPT) > 0
        assert "extractedOpinionList" in EXTRACTION_PROMPT

    def test_initial_labelling_prompt_exists(self):
        """Test that initial labelling prompt is defined."""
        assert INITIAL_LABELLING_PROMPT is not None
        assert len(INITIAL_LABELLING_PROMPT) > 0
        assert "KJ" in INITIAL_LABELLING_PROMPT

    def test_merge_labelling_prompt_exists(self):
        """Test that merge labelling prompt is defined."""
        assert MERGE_LABELLING_PROMPT is not None
        assert len(MERGE_LABELLING_PROMPT) > 0
        assert "クラスタ" in MERGE_LABELLING_PROMPT

    def test_overview_prompt_exists(self):
        """Test that overview prompt is defined."""
        assert OVERVIEW_PROMPT is not None
        assert len(OVERVIEW_PROMPT) > 0
        assert "リサーチアシスタント" in OVERVIEW_PROMPT

    def test_default_prompts_mapping(self):
        """Test that DEFAULT_PROMPTS maps step names to prompts."""
        assert "extraction" in DEFAULT_PROMPTS
        assert "hierarchical_initial_labelling" in DEFAULT_PROMPTS
        assert "hierarchical_merge_labelling" in DEFAULT_PROMPTS
        assert "hierarchical_overview" in DEFAULT_PROMPTS

    def test_get_default_prompt_extraction(self):
        """Test get_default_prompt for extraction step."""
        prompt = get_default_prompt("extraction")
        assert prompt == EXTRACTION_PROMPT

    def test_get_default_prompt_initial_labelling(self):
        """Test get_default_prompt for initial labelling step."""
        prompt = get_default_prompt("hierarchical_initial_labelling")
        assert prompt == INITIAL_LABELLING_PROMPT

    def test_get_default_prompt_merge_labelling(self):
        """Test get_default_prompt for merge labelling step."""
        prompt = get_default_prompt("hierarchical_merge_labelling")
        assert prompt == MERGE_LABELLING_PROMPT

    def test_get_default_prompt_overview(self):
        """Test get_default_prompt for overview step."""
        prompt = get_default_prompt("hierarchical_overview")
        assert prompt == OVERVIEW_PROMPT

    def test_get_default_prompt_unknown_step(self):
        """Test get_default_prompt returns None for unknown step."""
        assert get_default_prompt("unknown_step") is None
        assert get_default_prompt("embedding") is None  # No LLM
        assert get_default_prompt("hierarchical_clustering") is None


class TestPromptsInConfig:
    """Tests for default prompts in pipeline configuration."""

    def test_initialization_adds_default_prompts(self, tmp_path: Path):
        """Test that initialization adds default prompts when not provided."""
        from analysis_core.core.orchestration import initialization

        # Create minimal config without prompts
        config_path = tmp_path / "test.json"
        config_path.write_text(json.dumps({
            "input": "test",
            "question": "Test question?",
            "provider": "openai",
        }))

        config = initialization(
            config_path=config_path,
            skip_interaction=True,
            output_base_dir=tmp_path / "outputs",
            input_base_dir=tmp_path / "inputs",
        )

        # Check that default prompts were added
        assert config["extraction"]["prompt"] == EXTRACTION_PROMPT
        assert config["hierarchical_initial_labelling"]["prompt"] == INITIAL_LABELLING_PROMPT
        assert config["hierarchical_merge_labelling"]["prompt"] == MERGE_LABELLING_PROMPT
        assert config["hierarchical_overview"]["prompt"] == OVERVIEW_PROMPT

    def test_initialization_preserves_custom_prompts(self, tmp_path: Path):
        """Test that initialization preserves custom prompts."""
        from analysis_core.core.orchestration import initialization

        custom_prompt = "Custom extraction prompt"

        # Create config with custom prompt
        config_path = tmp_path / "test.json"
        config_path.write_text(json.dumps({
            "input": "test",
            "question": "Test question?",
            "provider": "openai",
            "extraction": {
                "prompt": custom_prompt,
            },
        }))

        config = initialization(
            config_path=config_path,
            skip_interaction=True,
            output_base_dir=tmp_path / "outputs",
            input_base_dir=tmp_path / "inputs",
        )

        # Custom prompt should be preserved
        assert config["extraction"]["prompt"] == custom_prompt
        # Other steps should still use defaults
        assert config["hierarchical_initial_labelling"]["prompt"] == INITIAL_LABELLING_PROMPT
