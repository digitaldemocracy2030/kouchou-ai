"""Tests for output JSON validation."""

import json
from pathlib import Path

import pytest

from broadlistening.pipeline.schemas.output_schema import (
    ArgumentSchema,
    ClusterSchema,
    HierarchicalResultSchema,
    StatusSchema,
    validate_output_json,
    validate_status_json,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestArgumentSchema:
    """Tests for ArgumentSchema."""

    def test_valid_argument(self):
        """Test valid argument schema."""
        arg = ArgumentSchema(
            arg_id="A0_0",
            argument="Test argument",
            comment_id=0,
            x=1.5,
            y=2.5,
            p=0,
            cluster_ids=["0", "1_5"],
        )
        assert arg.arg_id == "A0_0"
        assert arg.argument == "Test argument"
        assert len(arg.cluster_ids) == 2


class TestClusterSchema:
    """Tests for ClusterSchema."""

    def test_valid_cluster(self):
        """Test valid cluster schema."""
        cluster = ClusterSchema(id="0", label="Test Cluster", description="A test cluster", level=0)
        assert cluster.id == "0"
        assert cluster.label == "Test Cluster"
        assert cluster.level == 0


class TestHierarchicalResultSchema:
    """Tests for HierarchicalResultSchema."""

    def test_valid_result(self):
        """Test valid hierarchical result."""
        result = HierarchicalResultSchema(
            arguments=[
                ArgumentSchema(
                    arg_id="A0_0", argument="Test", comment_id=0, x=1.0, y=2.0, p=0, cluster_ids=["0"]
                )
            ],
            clusters=[ClusterSchema(id="0", label="Test", description="Test cluster", level=0)],
            propertyMaps={"source": {"Google Form": ["A0_0"]}},
            intro="Test intro",
            overview="Test overview",
        )
        assert len(result.arguments) == 1
        assert len(result.clusters) == 1
        assert result.intro == "Test intro"

    def test_from_json_file_not_found(self):
        """Test loading non-existent output file."""
        filepath = FIXTURES_DIR / "nonexistent_output.json"
        with pytest.raises(FileNotFoundError, match="Output file not found"):
            HierarchicalResultSchema.from_json_file(str(filepath))


class TestStatusSchema:
    """Tests for StatusSchema."""

    def test_valid_status_completed(self):
        """Test valid completed status."""
        status = StatusSchema(
            status="completed",
            start_time="2024-01-01T10:00:00",
            end_time="2024-01-01T10:30:00",
            total_token_usage=15000,
            token_usage_input=10000,
            token_usage_output=5000,
            estimated_cost=0.025,
            provider="openai",
            model="gpt-4o-mini",
            completed_jobs=[{"step": "extraction", "completed": "2024-01-01T10:05:00", "duration": 300}],
        )
        assert status.status == "completed"
        assert status.total_token_usage == 15000
        assert len(status.completed_jobs) == 1

    def test_valid_status_error(self):
        """Test valid error status."""
        status = StatusSchema(
            status="error",
            start_time="2024-01-01T10:00:00",
            end_time="2024-01-01T10:05:00",
            error="Test error message",
            error_stack_trace="Traceback...",
        )
        assert status.status == "error"
        assert status.error == "Test error message"

    def test_default_values(self):
        """Test default values."""
        status = StatusSchema(status="running", start_time="2024-01-01T10:00:00")
        assert status.total_token_usage == 0
        assert status.estimated_cost == 0.0
        assert len(status.completed_jobs) == 0


class TestValidateOutputJSON:
    """Tests for validate_output_json function."""

    def test_validate_nonexistent_file(self):
        """Test validating non-existent output file."""
        filepath = FIXTURES_DIR / "nonexistent_output.json"
        result = validate_output_json(str(filepath))
        assert result["valid"] is False
        assert "Output file not found" in result["message"]
        assert result["output"] is None


class TestValidateStatusJSON:
    """Tests for validate_status_json function."""

    def test_validate_nonexistent_file(self):
        """Test validating non-existent status file."""
        filepath = FIXTURES_DIR / "nonexistent_status.json"
        result = validate_status_json(str(filepath))
        assert result["valid"] is False
        assert "Status file not found" in result["message"]
        assert result["status"] is None


class TestOutputValidationIntegration:
    """Integration tests for output validation."""

    def test_create_and_validate_output(self, tmp_path):
        """Test creating and validating output file."""
        output_data = {
            "arguments": [
                {
                    "arg_id": "A0_0",
                    "argument": "Test argument",
                    "comment_id": 0,
                    "x": 1.5,
                    "y": 2.5,
                    "p": 0,
                    "cluster_ids": ["0"],
                }
            ],
            "clusters": [{"id": "0", "label": "Test Cluster", "description": "A test cluster", "level": 0}],
            "propertyMaps": {"source": {"Google Form": ["A0_0"]}},
            "intro": "Test intro",
            "overview": "Test overview",
        }

        output_file = tmp_path / "test_output.json"
        with open(output_file, "w") as f:
            json.dump(output_data, f)

        result = validate_output_json(str(output_file))
        assert result["valid"] is True
        assert "1 arguments" in result["message"]
        assert "1 clusters" in result["message"]

    def test_create_and_validate_status(self, tmp_path):
        """Test creating and validating status file."""
        status_data = {
            "status": "completed",
            "start_time": "2024-01-01T10:00:00",
            "end_time": "2024-01-01T10:30:00",
            "total_token_usage": 15000,
            "token_usage_input": 10000,
            "token_usage_output": 5000,
            "estimated_cost": 0.025,
            "provider": "openai",
            "model": "gpt-4o-mini",
            "completed_jobs": [],
        }

        status_file = tmp_path / "test_status.json"
        with open(status_file, "w") as f:
            json.dump(status_data, f)

        result = validate_status_json(str(status_file))
        assert result["valid"] is True
        assert "completed" in result["message"]
