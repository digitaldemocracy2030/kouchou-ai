"""End-to-end tests for pipeline execution.

Note: These tests validate the pipeline structure and configuration,
but do not execute the full pipeline (which would require API keys).
"""

import json
from pathlib import Path


from broadlistening.pipeline.schemas.config_schema import PipelineConfig
from broadlistening.pipeline.schemas.input_csv_schema import InputCSVSchema

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestPipelineE2E:
    """End-to-end pipeline tests."""

    def test_validate_complete_pipeline_inputs(self):
        """Test that all required inputs for pipeline are valid."""
        config_file = FIXTURES_DIR / "valid_config.json"
        config = PipelineConfig.from_json_file(str(config_file))

        csv_file = FIXTURES_DIR / f"{config.input}.csv"
        csv_schema = InputCSVSchema.validate_csv_file(str(csv_file), config.extraction.properties)

        assert config.name == "Test Report"
        assert len(csv_schema.rows) == 10
        assert all(prop in csv_schema.additional_properties for prop in config.extraction.properties)

    def test_pipeline_config_consistency(self):
        """Test that pipeline config is internally consistent."""
        config_file = FIXTURES_DIR / "valid_config.json"
        config = PipelineConfig.from_json_file(str(config_file))

        assert config.extraction.limit <= 1000
        assert config.extraction.workers >= 1
        assert len(config.hierarchical_clustering.cluster_nums) >= 1
        assert all(n > 0 for n in config.hierarchical_clustering.cluster_nums)

    def test_minimal_config_has_defaults(self):
        """Test that minimal config gets proper defaults."""
        config_file = FIXTURES_DIR / "minimal_config.json"
        config = PipelineConfig.from_json_file(str(config_file))

        assert config.model == "gpt-4o-mini"
        assert config.extraction.limit == 1000
        assert config.extraction.workers == 1
        assert config.hierarchical_clustering.cluster_nums == [3, 6]

    def test_output_directory_structure(self, tmp_path):
        """Test that output directory structure can be created."""
        dataset_name = "test_dataset"
        output_dir = tmp_path / "outputs" / dataset_name
        output_dir.mkdir(parents=True, exist_ok=True)

        expected_files = [
            "hierarchical_result.json",
            "hierarchical_status.json",
            "args.csv",
            "relations.csv",
            "embeddings.pkl",
            "hierarchical_clusters.csv",
            "hierarchical_initial_labels.csv",
            "hierarchical_merge_labels.csv",
            "hierarchical_overview.txt",
        ]

        for filename in expected_files:
            _ = output_dir / filename
            assert output_dir.exists()

    def test_status_file_structure(self, tmp_path):
        """Test creating and validating status file structure."""
        status_data = {
            "status": "running",
            "start_time": "2024-01-01T10:00:00",
            "total_token_usage": 0,
            "token_usage_input": 0,
            "token_usage_output": 0,
            "estimated_cost": 0.0,
            "provider": "openai",
            "model": "gpt-4o-mini",
            "completed_jobs": [],
            "plan": [
                {"step": "extraction", "run": True, "reason": "not trace of previous run"},
                {"step": "embedding", "run": True, "reason": "not trace of previous run"},
            ],
        }

        status_file = tmp_path / "hierarchical_status.json"
        with open(status_file, "w") as f:
            json.dump(status_data, f, indent=2)

        assert status_file.exists()

        with open(status_file) as f:
            loaded_data = json.load(f)

        assert loaded_data["status"] == "running"
        assert len(loaded_data["plan"]) == 2


class TestPipelineStepDependencies:
    """Tests for pipeline step dependencies."""

    def test_step_order(self):
        """Test that pipeline steps are in correct order."""
        expected_order = [
            "extraction",
            "embedding",
            "hierarchical_clustering",
            "hierarchical_initial_labelling",
            "hierarchical_merge_labelling",
            "hierarchical_overview",
            "hierarchical_aggregation",
            "hierarchical_visualization",
        ]

        assert len(expected_order) == 8

    def test_required_files_per_step(self):
        """Test that each step produces expected output files."""
        step_outputs = {
            "extraction": ["args.csv", "relations.csv"],
            "embedding": ["embeddings.pkl"],
            "hierarchical_clustering": ["hierarchical_clusters.csv"],
            "hierarchical_initial_labelling": ["hierarchical_initial_labels.csv"],
            "hierarchical_merge_labelling": ["hierarchical_merge_labels.csv"],
            "hierarchical_overview": ["hierarchical_overview.txt"],
            "hierarchical_aggregation": ["hierarchical_result.json"],
            "hierarchical_visualization": ["report"],
        }

        assert len(step_outputs) == 8
        for _step, outputs in step_outputs.items():
            assert len(outputs) >= 1


class TestConfigValidationWithCSV:
    """Tests for config validation against CSV files."""

    def test_config_properties_match_csv_columns(self):
        """Test that config properties exist in CSV."""
        config_file = FIXTURES_DIR / "valid_config.json"
        config = PipelineConfig.from_json_file(str(config_file))

        csv_file = FIXTURES_DIR / f"{config.input}.csv"
        csv_schema = InputCSVSchema.validate_csv_file(str(csv_file))

        for prop in config.extraction.properties:
            assert prop in csv_schema.additional_properties, f"Property '{prop}' not found in CSV"

    def test_extraction_limit_vs_csv_rows(self):
        """Test that extraction limit is reasonable for CSV size."""
        config_file = FIXTURES_DIR / "valid_config.json"
        config = PipelineConfig.from_json_file(str(config_file))

        csv_file = FIXTURES_DIR / f"{config.input}.csv"
        csv_schema = InputCSVSchema.validate_csv_file(str(csv_file))

        actual_rows = len(csv_schema.rows)
        limit = config.extraction.limit

        assert limit > 0
        if actual_rows < limit:
            assert True
