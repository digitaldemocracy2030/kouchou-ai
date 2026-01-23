"""Tests for compatibility layer."""

import pytest

from analysis_core.compat import normalize_config, create_step_context_from_config


class TestNormalizeConfig:
    """Tests for normalize_config function."""

    def test_fills_top_level_defaults(self):
        """Test that top-level defaults are filled in."""
        config = {}
        result = normalize_config(config)

        assert result["model"] == "gpt-4o-mini"
        assert result["provider"] == "openai"
        assert result["is_embedded_at_local"] is False
        assert result["is_pubcom"] is False

    def test_fills_extraction_defaults(self):
        """Test that extraction defaults are filled in."""
        config = {}
        result = normalize_config(config)

        assert "extraction" in result
        assert result["extraction"]["limit"] == 1000
        assert result["extraction"]["workers"] == 3
        assert result["extraction"]["model"] == "gpt-4o-mini"
        assert "prompt" in result["extraction"]
        assert len(result["extraction"]["prompt"]) > 0

    def test_fills_embedding_defaults(self):
        """Test that embedding defaults are filled in."""
        config = {}
        result = normalize_config(config)

        assert "embedding" in result
        assert result["embedding"]["model"] == "text-embedding-3-small"

    def test_fills_clustering_defaults(self):
        """Test that clustering defaults are filled in."""
        config = {}
        result = normalize_config(config)

        assert "hierarchical_clustering" in result
        assert result["hierarchical_clustering"]["cluster_nums"] == [3, 6]

    def test_fills_labelling_defaults(self):
        """Test that labelling defaults are filled in."""
        config = {}
        result = normalize_config(config)

        assert "hierarchical_initial_labelling" in result
        assert "hierarchical_merge_labelling" in result
        assert result["hierarchical_initial_labelling"]["sampling_num"] == 10
        assert result["hierarchical_merge_labelling"]["sampling_num"] == 10

    def test_includes_source_code_by_default(self):
        """Test that source code is included by default (Analysis screen compatibility)."""
        config = {}
        result = normalize_config(config)

        # All steps should have source_code for Analysis screen
        steps = [
            "extraction",
            "embedding",
            "hierarchical_clustering",
            "hierarchical_initial_labelling",
            "hierarchical_merge_labelling",
            "hierarchical_overview",
            "hierarchical_aggregation",
            "hierarchical_visualization",
        ]

        for step in steps:
            assert step in result, f"Step {step} not in result"
            assert "source_code" in result[step], f"source_code not in {step}"
            assert len(result[step]["source_code"]) > 0, f"source_code empty for {step}"

    def test_source_code_can_be_disabled(self):
        """Test that source code inclusion can be disabled."""
        config = {}
        result = normalize_config(config, include_source_code=False)

        # source_code should not be added when disabled
        assert "source_code" not in result["extraction"]
        assert "source_code" not in result["embedding"]

    def test_preserves_existing_values(self):
        """Test that existing values are preserved."""
        config = {
            "model": "gpt-4o",
            "extraction": {
                "limit": 500,
                "prompt": "Custom prompt",
            },
        }
        result = normalize_config(config)

        assert result["model"] == "gpt-4o"
        assert result["extraction"]["limit"] == 500
        assert result["extraction"]["prompt"] == "Custom prompt"
        # But workers should be filled with default
        assert result["extraction"]["workers"] == 3


class TestCreateStepContextFromConfig:
    """Tests for create_step_context_from_config function."""

    def test_creates_context_from_minimal_config(self):
        """Test creating StepContext from minimal config."""
        config = {"name": "test-analysis"}
        ctx = create_step_context_from_config(config)

        assert ctx.dataset == "test-analysis"
        assert ctx.provider == "openai"
        assert ctx.model == "gpt-4o-mini"

    def test_uses_config_values(self):
        """Test that config values are used in context."""
        config = {
            "output_dir": "my-output",
            "provider": "azure",
            "model": "gpt-4o",
            "local_llm_address": "http://localhost:11434",
        }
        ctx = create_step_context_from_config(config)

        assert ctx.dataset == "my-output"
        assert ctx.provider == "azure"
        assert ctx.model == "gpt-4o"
        assert ctx.local_llm_address == "http://localhost:11434"

    def test_output_dir_override(self):
        """Test that output_dir parameter overrides config."""
        config = {"output_dir": "config-output"}
        ctx = create_step_context_from_config(config, output_dir="override-output")

        assert ctx.dataset == "override-output"
