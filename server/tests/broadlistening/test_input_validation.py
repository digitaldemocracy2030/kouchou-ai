"""Tests for input CSV validation."""

import os
from pathlib import Path

import pandas as pd
import pytest

from broadlistening.pipeline.schemas.input_csv_schema import (
    InputCSVRow,
    InputCSVSchema,
    validate_input_csv,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestInputCSVRow:
    """Tests for InputCSVRow schema."""

    def test_valid_row(self):
        """Test valid CSV row."""
        row = InputCSVRow(**{"comment-id": 1, "comment-body": "This is a test comment"})
        assert row.comment_id == 1
        assert row.comment_body == "This is a test comment"

    def test_empty_comment_body(self):
        """Test that empty comment body raises error."""
        with pytest.raises(ValueError, match="comment-body must not be empty"):
            InputCSVRow(**{"comment-id": 1, "comment-body": ""})

    def test_whitespace_only_comment_body(self):
        """Test that whitespace-only comment body raises error."""
        with pytest.raises(ValueError, match="comment-body must not be empty"):
            InputCSVRow(**{"comment-id": 1, "comment-body": "   "})


class TestInputCSVSchema:
    """Tests for InputCSVSchema."""

    def test_from_dataframe_valid(self):
        """Test creating schema from valid DataFrame."""
        df = pd.DataFrame(
            {
                "comment-id": [1, 2, 3],
                "comment-body": ["Comment 1", "Comment 2", "Comment 3"],
                "source": ["Google Form", "X API", "Google Form"],
            }
        )
        schema = InputCSVSchema.from_dataframe(df)
        assert len(schema.rows) == 3
        assert "source" in schema.additional_properties

    def test_from_dataframe_missing_required_column(self):
        """Test that missing required column raises error."""
        df = pd.DataFrame({"comment-id": [1, 2, 3], "source": ["A", "B", "C"]})
        with pytest.raises(ValueError, match="Missing required columns"):
            InputCSVSchema.from_dataframe(df)

    def test_from_dataframe_missing_required_property(self):
        """Test that missing required property raises error."""
        df = pd.DataFrame(
            {"comment-id": [1, 2, 3], "comment-body": ["Comment 1", "Comment 2", "Comment 3"], "source": ["A", "B", "C"]}
        )
        with pytest.raises(ValueError, match="Missing required property columns"):
            InputCSVSchema.from_dataframe(df, required_properties=["age"])

    def test_validate_csv_file_valid(self):
        """Test validating a valid CSV file."""
        filepath = FIXTURES_DIR / "valid_input.csv"
        schema = InputCSVSchema.validate_csv_file(str(filepath))
        assert len(schema.rows) == 10
        assert "source" in schema.additional_properties
        assert "age" in schema.additional_properties

    def test_validate_csv_file_missing_column(self):
        """Test validating CSV file with missing column."""
        filepath = FIXTURES_DIR / "invalid_input_missing_column.csv"
        with pytest.raises(ValueError, match="Missing required columns"):
            InputCSVSchema.validate_csv_file(str(filepath))

    def test_validate_csv_file_empty(self):
        """Test validating empty CSV file."""
        filepath = FIXTURES_DIR / "invalid_input_empty.csv"
        with pytest.raises(ValueError, match="CSV file is empty"):
            InputCSVSchema.validate_csv_file(str(filepath))

    def test_validate_csv_file_not_found(self):
        """Test validating non-existent CSV file."""
        filepath = FIXTURES_DIR / "nonexistent.csv"
        with pytest.raises(FileNotFoundError, match="CSV file not found"):
            InputCSVSchema.validate_csv_file(str(filepath))


class TestValidateInputCSV:
    """Tests for validate_input_csv function."""

    def test_validate_valid_csv(self):
        """Test validating a valid CSV file."""
        filepath = FIXTURES_DIR / "valid_input.csv"
        result = validate_input_csv(str(filepath))
        assert result["valid"] is True
        assert "10 rows" in result["message"]
        assert result["schema"] is not None
        assert len(result["errors"]) == 0

    def test_validate_invalid_csv(self):
        """Test validating an invalid CSV file."""
        filepath = FIXTURES_DIR / "invalid_input_missing_column.csv"
        result = validate_input_csv(str(filepath))
        assert result["valid"] is False
        assert "Missing required columns" in result["message"]
        assert result["schema"] is None
        assert len(result["errors"]) > 0

    def test_validate_with_required_properties(self):
        """Test validating CSV with required properties."""
        filepath = FIXTURES_DIR / "valid_input.csv"
        result = validate_input_csv(str(filepath), required_properties=["source", "age"])
        assert result["valid"] is True

    def test_validate_missing_required_properties(self):
        """Test validating CSV missing required properties."""
        filepath = FIXTURES_DIR / "valid_input.csv"
        result = validate_input_csv(str(filepath), required_properties=["nonexistent_property"])
        assert result["valid"] is False
        assert "Missing required property columns" in result["message"]
