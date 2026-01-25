"""Integration tests for pipeline with custom paths.

These tests verify that the pipeline correctly uses configurable paths
throughout the entire execution flow, not just in individual step functions.

This is a regression test for bugs where:
- Step functions used hardcoded 'inputs/' or 'outputs/' paths
- update_status/update_progress didn't read _output_base_dir from config
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest


class TestPipelinePathsIntegration:
    """Integration tests for pipeline path handling."""

    @pytest.fixture
    def temp_dirs(self):
        """Create temporary directories for testing."""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            # Use non-standard names to catch hardcoded paths
            input_dir = base / "custom_inputs_location"
            output_dir = base / "custom_outputs_location"
            input_dir.mkdir(parents=True)
            output_dir.mkdir(parents=True)
            yield {
                "base": base,
                "input_dir": input_dir,
                "output_dir": output_dir,
            }

    @pytest.fixture
    def sample_input_csv(self, temp_dirs):
        """Create a sample input CSV file."""
        input_file = temp_dirs["input_dir"] / "test_input.csv"
        df = pd.DataFrame(
            {
                "comment-id": ["1", "2", "3"],
                "comment-body": [
                    "This is a test comment about AI",
                    "Another comment about technology",
                    "A third comment about innovation",
                ],
            }
        )
        df.to_csv(input_file, index=False)
        return input_file

    @pytest.fixture
    def sample_config(self, temp_dirs):
        """Create a sample pipeline configuration."""
        return {
            "input": "test_input",
            "output_dir": "test_output",
            "question": "What are the main topics?",
            "provider": "openai",
            "model": "gpt-4o-mini",
            "_input_base_dir": str(temp_dirs["input_dir"]),
            "_output_base_dir": str(temp_dirs["output_dir"]),
            "is_pubcom": False,
            "is_embedded_at_local": False,
            "plan": [
                {"step": "extraction", "run": True},
            ],
            "extraction": {
                "model": "gpt-4o-mini",
                "prompt": "Extract arguments",
                "workers": 1,
                "limit": 10,
                "properties": [],
                "categories": {},
            },
            "embedding": {
                "model": "text-embedding-3-small",
            },
            "hierarchical_aggregation": {
                "hidden_properties": {},
            },
        }

    def test_update_status_uses_config_output_base_dir(self, temp_dirs, sample_config):
        """Test that update_status reads _output_base_dir from config."""
        from analysis_core.core.orchestration import update_status

        # Create the output subdirectory
        output_subdir = temp_dirs["output_dir"] / sample_config["output_dir"]
        output_subdir.mkdir(parents=True)

        # Call update_status without passing output_base_dir
        # It should read from config["_output_base_dir"]
        update_status(sample_config, {"status": "running"})

        # Verify status file was created in the correct location
        status_file = output_subdir / "hierarchical_status.json"
        assert status_file.exists(), f"Status file not found at {status_file}"

        # Verify hardcoded path was NOT used
        hardcoded_path = Path("outputs") / sample_config["output_dir"] / "hierarchical_status.json"
        assert not hardcoded_path.exists(), "Status file was created at hardcoded path!"

    def test_update_progress_uses_config_output_base_dir(self, temp_dirs, sample_config):
        """Test that update_progress reads _output_base_dir from config."""
        from analysis_core.core.orchestration import update_progress

        # Create the output subdirectory
        output_subdir = temp_dirs["output_dir"] / sample_config["output_dir"]
        output_subdir.mkdir(parents=True)

        # Initialize required config fields
        sample_config["current_job_progress"] = 0

        # Call update_progress without passing output_base_dir
        update_progress(sample_config, total=10)

        # Verify status file was updated in the correct location
        status_file = output_subdir / "hierarchical_status.json"
        assert status_file.exists(), f"Status file not found at {status_file}"

        with open(status_file) as f:
            status = json.load(f)
        assert status["current_jop_tasks"] == 10

    def test_extraction_step_uses_config_paths(self, temp_dirs, sample_input_csv, sample_config):
        """Test that extraction step reads from correct input path."""
        # Track which paths are accessed
        read_csv_calls = []
        original_read_csv = pd.read_csv

        def tracking_read_csv(path, *args, **kwargs):
            read_csv_calls.append(str(path))
            return original_read_csv(path, *args, **kwargs)

        # Patch read_csv in the extraction module's namespace
        with patch("analysis_core.steps.extraction.pd.read_csv", side_effect=tracking_read_csv):
            # Import after patching
            from analysis_core.steps.extraction import extraction

            # Create status file for update_progress
            output_subdir = temp_dirs["output_dir"] / sample_config["output_dir"]
            output_subdir.mkdir(parents=True, exist_ok=True)
            status_file = output_subdir / "hierarchical_status.json"
            with open(status_file, "w") as f:
                json.dump(sample_config, f)

            # The function will fail when trying to call LLM, but that's OK
            # We just want to verify it reads from the correct path
            try:
                extraction(sample_config)
            except Exception:
                pass  # Expected - we're not mocking LLM

        # Verify input file was read from config path
        expected_input_path = f"{temp_dirs['input_dir']}/test_input.csv"
        input_reads = [c for c in read_csv_calls if "test_input.csv" in c]
        assert len(input_reads) > 0, f"Input file not read. Calls: {read_csv_calls}"
        assert expected_input_path in input_reads[0], (
            f"Wrong input path. Expected {expected_input_path}, got {input_reads[0]}"
        )

        # Verify hardcoded 'inputs/' was NOT used
        for call in read_csv_calls:
            if "test_input.csv" in call:
                assert not call.startswith("inputs/"), f"Hardcoded 'inputs/' path used: {call}"

    def test_embedding_step_uses_config_paths(self, temp_dirs, sample_config):
        """Test that embedding step uses paths from config."""
        from analysis_core.steps.embedding import embedding

        # Create the output subdirectory
        output_subdir = temp_dirs["output_dir"] / sample_config["output_dir"]
        output_subdir.mkdir(parents=True)

        # Create args.csv that embedding needs
        args_df = pd.DataFrame(
            {
                "arg-id": ["arg1", "arg2"],
                "argument": ["Test argument 1", "Test argument 2"],
            }
        )
        args_df.to_csv(output_subdir / "args.csv", index=False)

        # Mock the embedding call
        with patch("analysis_core.steps.embedding.request_to_embed") as mock_embed:
            mock_embed.return_value = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]

            # Run embedding
            embedding(sample_config)

        # Verify output file was created in the correct location
        embeddings_file = output_subdir / "embeddings.pkl"
        assert embeddings_file.exists(), f"embeddings.pkl not found at {embeddings_file}"

        # Verify hardcoded path was NOT used
        hardcoded_embeddings = Path("outputs") / sample_config["output_dir"] / "embeddings.pkl"
        assert not hardcoded_embeddings.exists(), "embeddings.pkl was created at hardcoded path!"

    def test_hierarchical_clustering_uses_config_paths(self, temp_dirs, sample_config):
        """Test that hierarchical_clustering step uses paths from config."""
        from analysis_core.steps.hierarchical_clustering import hierarchical_clustering

        # Create the output subdirectory
        output_subdir = temp_dirs["output_dir"] / sample_config["output_dir"]
        output_subdir.mkdir(parents=True)

        # Create required input files
        args_df = pd.DataFrame(
            {
                "arg-id": [f"arg{i}" for i in range(20)],
                "argument": [f"Test argument {i}" for i in range(20)],
            }
        )
        args_df.to_csv(output_subdir / "args.csv", index=False)

        # Create embeddings with enough dimensions for UMAP
        import numpy as np

        embeddings_df = pd.DataFrame(
            {
                "arg-id": [f"arg{i}" for i in range(20)],
                "embedding": [np.random.rand(100).tolist() for _ in range(20)],
            }
        )
        embeddings_df.to_pickle(output_subdir / "embeddings.pkl")

        # Add clustering config
        sample_config["hierarchical_clustering"] = {
            "cluster_nums": [2, 4],
        }

        # Run hierarchical clustering
        hierarchical_clustering(sample_config)

        # Verify output file was created in the correct location
        clusters_file = output_subdir / "hierarchical_clusters.csv"
        assert clusters_file.exists(), f"hierarchical_clusters.csv not found at {clusters_file}"

        # Verify hardcoded path was NOT used
        hardcoded_clusters = Path("outputs") / sample_config["output_dir"] / "hierarchical_clusters.csv"
        assert not hardcoded_clusters.exists(), "hierarchical_clusters.csv was created at hardcoded path!"


class TestOrchestratorPathsIntegration:
    """Integration tests for PipelineOrchestrator path handling."""

    def test_orchestrator_passes_paths_to_steps(self):
        """Test that PipelineOrchestrator correctly passes paths to step functions."""
        from analysis_core import PipelineOrchestrator

        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            input_dir = base / "my_inputs"
            output_dir = base / "my_outputs"
            input_dir.mkdir()
            output_dir.mkdir()

            # Create config with paths already set (as they would be from from_config)
            config = {
                "input": "test",
                "question": "Test question?",
                "output_dir": "test",
                "provider": "openai",
                "plan": [{"step": "extraction", "run": True}],
                "_output_base_dir": str(output_dir),
                "_input_base_dir": str(input_dir),
            }

            # Create orchestrator with custom paths
            orchestrator = PipelineOrchestrator(
                config=config,
                output_base_dir=output_dir,
                input_base_dir=input_dir,
                steps=["extraction"],
            )

            # Verify paths are stored in orchestrator
            assert orchestrator.output_base_dir == output_dir
            assert orchestrator.input_base_dir == input_dir
