"""Test that all package modules can be imported correctly."""

import pytest


class TestCoreImports:
    """Test core module imports."""

    def test_main_package_imports(self):
        """Test main package exports."""
        from analysis_core import PipelineOrchestrator, PipelineConfig, __version__

        assert __version__ == "0.1.0"
        assert PipelineOrchestrator is not None
        assert PipelineConfig is not None

    def test_core_module_imports(self):
        """Test core orchestration utilities."""
        from analysis_core.core import (
            load_specs,
            get_specs,
            validate_config,
            decide_what_to_run,
            update_status,
            update_progress,
            run_step,
            termination,
        )

        assert load_specs is not None
        assert get_specs is not None
        assert validate_config is not None
        assert decide_what_to_run is not None
        assert update_status is not None
        assert update_progress is not None
        assert run_step is not None
        assert termination is not None

    def test_core_utils_imports(self):
        """Test core utility functions."""
        from analysis_core.core import (
            typed_message,
            messages,
            format_token_count,
            estimate_tokens,
            chunk_text,
        )

        assert typed_message is not None
        assert messages is not None
        assert format_token_count is not None
        assert estimate_tokens is not None
        assert chunk_text is not None


class TestServiceImports:
    """Test service module imports."""

    def test_llm_service_imports(self):
        """Test LLM service functions."""
        from analysis_core.services import request_to_chat_ai, request_to_embed

        assert request_to_chat_ai is not None
        assert request_to_embed is not None

    def test_parse_json_imports(self):
        """Test JSON parsing utilities."""
        from analysis_core.services import parse_extraction_response, parse_json_list

        assert parse_extraction_response is not None
        assert parse_json_list is not None


class TestStepImports:
    """Test pipeline step imports."""

    def test_extraction_step(self):
        """Test extraction step import."""
        from analysis_core.steps import extraction

        assert extraction is not None

    def test_embedding_step(self):
        """Test embedding step import."""
        from analysis_core.steps import embedding

        assert embedding is not None

    def test_clustering_step(self):
        """Test hierarchical clustering step import."""
        from analysis_core.steps import hierarchical_clustering

        assert hierarchical_clustering is not None

    def test_initial_labelling_step(self):
        """Test initial labelling step import."""
        from analysis_core.steps import hierarchical_initial_labelling

        assert hierarchical_initial_labelling is not None

    def test_merge_labelling_step(self):
        """Test merge labelling step import."""
        from analysis_core.steps import hierarchical_merge_labelling

        assert hierarchical_merge_labelling is not None

    def test_overview_step(self):
        """Test overview step import."""
        from analysis_core.steps import hierarchical_overview

        assert hierarchical_overview is not None

    def test_aggregation_step(self):
        """Test aggregation step import."""
        from analysis_core.steps import hierarchical_aggregation

        assert hierarchical_aggregation is not None

    def test_visualization_step(self):
        """Test visualization step import."""
        from analysis_core.steps import hierarchical_visualization

        assert hierarchical_visualization is not None

    def test_all_steps_from_init(self):
        """Test all steps can be imported from steps module."""
        from analysis_core.steps import (
            extraction,
            embedding,
            hierarchical_clustering,
            hierarchical_initial_labelling,
            hierarchical_merge_labelling,
            hierarchical_overview,
            hierarchical_aggregation,
            hierarchical_visualization,
        )

        steps = [
            extraction,
            embedding,
            hierarchical_clustering,
            hierarchical_initial_labelling,
            hierarchical_merge_labelling,
            hierarchical_overview,
            hierarchical_aggregation,
            hierarchical_visualization,
        ]
        assert all(step is not None for step in steps)
        assert len(steps) == 8


class TestConfigModule:
    """Test configuration module."""

    def test_config_classes(self):
        """Test configuration dataclasses."""
        from analysis_core.config import PipelineConfig, StepConfig, load_config, save_config

        assert PipelineConfig is not None
        assert StepConfig is not None
        assert load_config is not None
        assert save_config is not None

    def test_pipeline_config_creation(self):
        """Test PipelineConfig can be instantiated."""
        from pathlib import Path

        from analysis_core.config import PipelineConfig

        config = PipelineConfig(
            input_path=Path("test.csv"),
            output_dir=Path("output"),
            question="Test question",
        )
        assert config.input_path == Path("test.csv")
        assert config.output_dir == Path("output")
        assert config.question == "Test question"
        assert config.model == "gpt-4o-mini"  # default
        assert config.provider == "openai"  # default
