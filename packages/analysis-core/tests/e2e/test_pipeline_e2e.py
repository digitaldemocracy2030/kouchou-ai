"""End-to-end tests for the analysis pipeline.

These tests use real LLM API calls and validate that the pipeline
produces correctly structured output. They are not run automatically
to avoid API costs.

Usage:
    # Set API key and run tests
    OPENAI_API_KEY=sk-xxx pytest tests/e2e/ -v

    # Run with verbose output
    OPENAI_API_KEY=sk-xxx pytest tests/e2e/ -v -s

    # Run specific test
    OPENAI_API_KEY=sk-xxx pytest tests/e2e/test_pipeline_e2e.py::TestPipelineE2E::test_full_pipeline -v
"""

import json
import shutil
from pathlib import Path

import pandas as pd
import pytest

from .schemas import HierarchicalResult


@pytest.mark.e2e
class TestPipelineE2E:
    """End-to-end tests for the complete pipeline."""

    def test_full_pipeline_produces_valid_output(self, api_key, temp_dirs, small_comments_csv, pipeline_config):
        """Test that the full pipeline produces valid hierarchical_result.json.

        This test:
        1. Copies test input to temp directory
        2. Runs the complete pipeline with real LLM API calls
        3. Validates that output files exist
        4. Validates output structure using Pydantic schemas
        5. Performs basic consistency checks
        """
        from analysis_core import PipelineOrchestrator

        # Copy input file to temp input directory
        input_file = temp_dirs["input_dir"] / "small_comments.csv"
        shutil.copy(small_comments_csv, input_file)

        # Create output directory
        output_dir = temp_dirs["output_dir"] / pipeline_config["output_dir"]
        output_dir.mkdir(parents=True, exist_ok=True)

        # Run the pipeline
        orchestrator = PipelineOrchestrator.from_dict(
            config=pipeline_config,
            output_dir=pipeline_config["output_dir"],
            output_base_dir=temp_dirs["output_dir"],
            input_base_dir=temp_dirs["input_dir"],
        )

        result = orchestrator.run()

        # Verify pipeline completed successfully
        assert result.success, f"Pipeline failed: {result.error}"

        # Verify output files exist
        expected_files = [
            "args.csv",
            "embeddings.pkl",
            "hierarchical_clusters.csv",
            "hierarchical_merge_labels.csv",
            "hierarchical_overview.txt",
            "hierarchical_result.json",
        ]

        for filename in expected_files:
            filepath = output_dir / filename
            assert filepath.exists(), f"Expected output file not found: {filepath}"

        # Load and validate hierarchical_result.json
        result_path = output_dir / "hierarchical_result.json"
        with open(result_path) as f:
            result_data = json.load(f)

        # Validate using Pydantic schema
        hierarchical_result = HierarchicalResult(**result_data)

        # Run structural validation
        validation_errors = hierarchical_result.validate_structure()
        assert not validation_errors, f"Structure validation errors: {validation_errors}"

        # Additional consistency checks
        assert hierarchical_result.comment_num == 5, "Should have 5 comments"
        assert len(hierarchical_result.arguments) > 0, "Should have extracted at least 1 argument"
        assert len(hierarchical_result.clusters) > 1, "Should have at least 2 clusters (root + 1)"

    def test_extraction_produces_arguments(self, api_key, temp_dirs, small_comments_csv, pipeline_config):
        """Test that extraction step produces valid args.csv."""
        from analysis_core import PipelineOrchestrator

        # Copy input file
        input_file = temp_dirs["input_dir"] / "small_comments.csv"
        shutil.copy(small_comments_csv, input_file)

        # Create output directory
        output_dir = temp_dirs["output_dir"] / pipeline_config["output_dir"]
        output_dir.mkdir(parents=True, exist_ok=True)

        # Run only extraction step
        orchestrator = PipelineOrchestrator.from_dict(
            config=pipeline_config,
            output_dir=pipeline_config["output_dir"],
            output_base_dir=temp_dirs["output_dir"],
            input_base_dir=temp_dirs["input_dir"],
        )

        # Only register extraction step
        from analysis_core.steps import extraction

        orchestrator.steps = ["extraction"]
        orchestrator.register_step("extraction", extraction)

        result = orchestrator.run()
        assert result.success, f"Extraction failed: {result.error}"

        # Verify args.csv exists and has valid structure
        args_path = output_dir / "args.csv"
        assert args_path.exists(), "args.csv not created"

        args_df = pd.read_csv(args_path)

        # Verify required columns exist
        required_columns = ["arg-id", "argument"]
        for col in required_columns:
            assert col in args_df.columns, f"Missing column: {col}"

        # Verify we extracted at least one argument
        assert len(args_df) > 0, "No arguments extracted"

        # Verify arguments are non-empty strings
        for _, row in args_df.iterrows():
            assert isinstance(row["argument"], str) and len(row["argument"]) > 0, f"Invalid argument: {row['argument']}"

    def test_clustering_produces_hierarchy(self, api_key, temp_dirs, small_comments_csv, pipeline_config):
        """Test that clustering step produces valid hierarchical structure."""
        from analysis_core import PipelineOrchestrator

        # Copy input file
        input_file = temp_dirs["input_dir"] / "small_comments.csv"
        shutil.copy(small_comments_csv, input_file)

        # Run extraction and embedding first, then clustering
        orchestrator = PipelineOrchestrator.from_dict(
            config=pipeline_config,
            output_dir=pipeline_config["output_dir"],
            output_base_dir=temp_dirs["output_dir"],
            input_base_dir=temp_dirs["input_dir"],
        )

        # Run only up to clustering
        from analysis_core.steps import embedding, extraction, hierarchical_clustering

        orchestrator.steps = ["extraction", "embedding", "hierarchical_clustering"]
        orchestrator.register_step("extraction", extraction)
        orchestrator.register_step("embedding", embedding)
        orchestrator.register_step("hierarchical_clustering", hierarchical_clustering)

        result = orchestrator.run()
        assert result.success, f"Pipeline failed: {result.error}"

        # Verify clustering output
        output_dir = temp_dirs["output_dir"] / pipeline_config["output_dir"]
        clusters_path = output_dir / "hierarchical_clusters.csv"
        assert clusters_path.exists(), "hierarchical_clusters.csv not created"

        clusters_df = pd.read_csv(clusters_path)

        # Verify we have cluster assignments
        assert len(clusters_df) > 0, "No cluster assignments"

        # Verify cluster level columns exist
        cluster_cols = [c for c in clusters_df.columns if c.startswith("cluster-level-")]
        assert len(cluster_cols) > 0, "No cluster level columns found"


@pytest.mark.e2e
class TestOutputSchemaValidation:
    """Tests for validating output schema compliance."""

    def test_hierarchical_result_schema(self, api_key, temp_dirs, small_comments_csv, pipeline_config):
        """Test that hierarchical_result.json conforms to schema."""
        from analysis_core import PipelineOrchestrator

        # Setup
        input_file = temp_dirs["input_dir"] / "small_comments.csv"
        shutil.copy(small_comments_csv, input_file)

        # Run full pipeline
        orchestrator = PipelineOrchestrator.from_dict(
            config=pipeline_config,
            output_dir=pipeline_config["output_dir"],
            output_base_dir=temp_dirs["output_dir"],
            input_base_dir=temp_dirs["input_dir"],
        )
        result = orchestrator.run()
        assert result.success, f"Pipeline failed: {result.error}"

        # Load result
        output_dir = temp_dirs["output_dir"] / pipeline_config["output_dir"]
        result_path = output_dir / "hierarchical_result.json"

        with open(result_path) as f:
            result_data = json.load(f)

        # Validate all fields exist with correct types
        hierarchical_result = HierarchicalResult(**result_data)

        # Validate arguments
        for arg in hierarchical_result.arguments:
            assert isinstance(arg.arg_id, str), "arg_id should be string"
            assert isinstance(arg.argument, str), "argument should be string"
            assert isinstance(arg.x, float), "x should be float"
            assert isinstance(arg.y, float), "y should be float"
            assert isinstance(arg.cluster_ids, list), "cluster_ids should be list"

        # Validate clusters
        for cluster in hierarchical_result.clusters:
            assert isinstance(cluster.id, str), "cluster id should be string"
            assert isinstance(cluster.level, int), "level should be int"
            assert isinstance(cluster.label, str), "label should be string"
            assert isinstance(cluster.value, int), "value should be int"

        # Validate overview is non-empty
        assert len(hierarchical_result.overview.strip()) > 0, "overview should not be empty"

    def test_args_csv_schema(self, api_key, temp_dirs, small_comments_csv, pipeline_config):
        """Test that args.csv conforms to expected schema."""
        from analysis_core import PipelineOrchestrator

        # Setup
        input_file = temp_dirs["input_dir"] / "small_comments.csv"
        shutil.copy(small_comments_csv, input_file)

        # Run extraction only
        orchestrator = PipelineOrchestrator.from_dict(
            config=pipeline_config,
            output_dir=pipeline_config["output_dir"],
            output_base_dir=temp_dirs["output_dir"],
            input_base_dir=temp_dirs["input_dir"],
        )

        from analysis_core.steps import extraction

        orchestrator.steps = ["extraction"]
        orchestrator.register_step("extraction", extraction)

        result = orchestrator.run()
        assert result.success, f"Extraction failed: {result.error}"

        # Load and validate args.csv
        output_dir = temp_dirs["output_dir"] / pipeline_config["output_dir"]
        args_df = pd.read_csv(output_dir / "args.csv")

        # Required columns
        assert "arg-id" in args_df.columns, "Missing arg-id column"
        assert "argument" in args_df.columns, "Missing argument column"

        # Validate data types
        for idx, row in args_df.iterrows():
            assert pd.notna(row["arg-id"]), f"arg-id should not be null at row {idx}"
            assert pd.notna(row["argument"]), f"argument should not be null at row {idx}"
            assert len(str(row["argument"])) > 0, f"argument should not be empty at row {idx}"
