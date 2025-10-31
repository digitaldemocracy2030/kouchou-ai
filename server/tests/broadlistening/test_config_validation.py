"""Tests for config JSON validation."""

from pathlib import Path

import pytest

from broadlistening.pipeline.schemas.config_schema import (
    ExtractionConfig,
    HierarchicalClusteringConfig,
    PipelineConfig,
    validate_config_json,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestExtractionConfig:
    """Tests for ExtractionConfig schema."""

    def test_valid_config(self):
        """Test valid extraction config."""
        config = ExtractionConfig(limit=100, workers=2, properties=["source", "age"])
        assert config.limit == 100
        assert config.workers == 2
        assert config.properties == ["source", "age"]

    def test_default_values(self):
        """Test default values."""
        config = ExtractionConfig()
        assert config.limit == 1000
        assert config.workers == 1
        assert config.properties == []

    def test_negative_limit(self):
        """Test that negative limit raises error."""
        with pytest.raises(ValueError, match="limit must be positive"):
            ExtractionConfig(limit=-1)

    def test_zero_workers(self):
        """Test that zero workers raises error."""
        with pytest.raises(ValueError, match="workers must be positive"):
            ExtractionConfig(workers=0)


class TestHierarchicalClusteringConfig:
    """Tests for HierarchicalClusteringConfig schema."""

    def test_valid_config(self):
        """Test valid clustering config."""
        config = HierarchicalClusteringConfig(cluster_nums=[3, 6, 12])
        assert config.cluster_nums == [3, 6, 12]

    def test_default_values(self):
        """Test default values."""
        config = HierarchicalClusteringConfig()
        assert config.cluster_nums == [3, 6]

    def test_empty_cluster_nums(self):
        """Test that empty cluster_nums raises error."""
        with pytest.raises(ValueError, match="cluster_nums must not be empty"):
            HierarchicalClusteringConfig(cluster_nums=[])

    def test_negative_cluster_num(self):
        """Test that negative cluster number raises error."""
        with pytest.raises(ValueError, match="All cluster numbers must be positive"):
            HierarchicalClusteringConfig(cluster_nums=[3, -1, 6])


class TestPipelineConfig:
    """Tests for PipelineConfig schema."""

    def test_valid_minimal_config(self):
        """Test valid minimal config."""
        config = PipelineConfig(name="Test", question="What?", input="test_input")
        assert config.name == "Test"
        assert config.question == "What?"
        assert config.input == "test_input"
        assert config.model == "gpt-4o-mini"

    def test_valid_full_config(self):
        """Test valid full config."""
        config = PipelineConfig(
            name="Test Report",
            question="What are the opinions?",
            input="test_input",
            model="gpt-4o",
            provider="openai",
            extraction={"limit": 50, "workers": 2, "properties": ["source"]},
            hierarchical_clustering={"cluster_nums": [2, 4]},
        )
        assert config.extraction.limit == 50
        assert config.hierarchical_clustering.cluster_nums == [2, 4]

    def test_invalid_provider(self):
        """Test that invalid provider raises error."""
        with pytest.raises(ValueError, match="provider must be one of"):
            PipelineConfig(name="Test", question="What?", input="test_input", provider="invalid_provider")

    def test_from_json_file_valid(self):
        """Test loading valid config from JSON file."""
        filepath = FIXTURES_DIR / "valid_config.json"
        config = PipelineConfig.from_json_file(str(filepath))
        assert config.name == "Test Report"
        assert config.input == "valid_input"
        assert config.extraction.limit == 10

    def test_from_json_file_minimal(self):
        """Test loading minimal config from JSON file."""
        filepath = FIXTURES_DIR / "minimal_config.json"
        config = PipelineConfig.from_json_file(str(filepath))
        assert config.name == "Minimal Test Report"
        assert config.input == "valid_input"
        assert config.model == "gpt-4o-mini"

    def test_from_json_file_missing_field(self):
        """Test loading config with missing required field."""
        filepath = FIXTURES_DIR / "invalid_config_missing_field.json"
        with pytest.raises(ValueError):
            PipelineConfig.from_json_file(str(filepath))

    def test_from_json_file_wrong_type(self):
        """Test loading config with wrong type."""
        filepath = FIXTURES_DIR / "invalid_config_wrong_type.json"
        with pytest.raises(ValueError):
            PipelineConfig.from_json_file(str(filepath))

    def test_from_json_file_not_found(self):
        """Test loading non-existent config file."""
        filepath = FIXTURES_DIR / "nonexistent.json"
        with pytest.raises(FileNotFoundError, match="Config file not found"):
            PipelineConfig.from_json_file(str(filepath))


class TestValidateConfigJSON:
    """Tests for validate_config_json function."""

    def test_validate_valid_config(self):
        """Test validating a valid config file."""
        filepath = FIXTURES_DIR / "valid_config.json"
        result = validate_config_json(str(filepath))
        assert result["valid"] is True
        assert "valid_input" in result["message"]
        assert result["config"] is not None
        assert len(result["errors"]) == 0

    def test_validate_minimal_config(self):
        """Test validating a minimal config file."""
        filepath = FIXTURES_DIR / "minimal_config.json"
        result = validate_config_json(str(filepath))
        assert result["valid"] is True
        assert result["config"] is not None

    def test_validate_invalid_config(self):
        """Test validating an invalid config file."""
        filepath = FIXTURES_DIR / "invalid_config_missing_field.json"
        result = validate_config_json(str(filepath))
        assert result["valid"] is False
        assert result["config"] is None
        assert len(result["errors"]) > 0

    def test_validate_wrong_type_config(self):
        """Test validating config with wrong type."""
        filepath = FIXTURES_DIR / "invalid_config_wrong_type.json"
        result = validate_config_json(str(filepath))
        assert result["valid"] is False
        assert result["config"] is None
