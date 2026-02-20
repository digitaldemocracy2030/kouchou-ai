"""Test that empty/whitespace-only comments are filtered out in extraction step (#583)."""

import polars as pl
import pytest

from analysis_core.steps.extraction import _filter_empty_comments


class TestEmptyCommentFiltering:
    """Test filtering of empty/whitespace-only comments before LLM processing."""

    def test_filters_empty_strings(self):
        """Empty string comments should be removed."""
        df = pl.DataFrame([
            {"comment-id": "1", "comment-body": "valid comment"},
            {"comment-id": "2", "comment-body": ""},
            {"comment-id": "3", "comment-body": "another valid comment"},
        ])
        result = _filter_empty_comments(df)
        assert len(result) == 2
        assert result["comment-id"].to_list() == ["1", "3"]

    def test_filters_whitespace_only(self):
        """Whitespace-only comments should be removed."""
        df = pl.DataFrame([
            {"comment-id": "1", "comment-body": "valid comment"},
            {"comment-id": "2", "comment-body": "   "},
            {"comment-id": "3", "comment-body": "\t\n"},
        ])
        result = _filter_empty_comments(df)
        assert len(result) == 1
        assert result["comment-id"].to_list() == ["1"]

    def test_keeps_valid_comments(self):
        """Valid comments should not be filtered out."""
        df = pl.DataFrame([
            {"comment-id": "1", "comment-body": "first comment"},
            {"comment-id": "2", "comment-body": "second comment"},
            {"comment-id": "3", "comment-body": "third comment"},
        ])
        result = _filter_empty_comments(df)
        assert len(result) == 3

    def test_all_empty_raises_error(self):
        """When all comments are empty, a RuntimeError should be raised."""
        df = pl.DataFrame([
            {"comment-id": "1", "comment-body": ""},
            {"comment-id": "2", "comment-body": "   "},
            {"comment-id": "3", "comment-body": "\n"},
        ])
        with pytest.raises(RuntimeError, match="All comments are empty"):
            _filter_empty_comments(df)

    def test_mixed_empty_and_valid(self):
        """Mixed input should keep only valid comments."""
        df = pl.DataFrame([
            {"comment-id": "1", "comment-body": "valid"},
            {"comment-id": "2", "comment-body": ""},
            {"comment-id": "3", "comment-body": "   "},
            {"comment-id": "4", "comment-body": "also valid"},
            {"comment-id": "5", "comment-body": "\n\n"},
        ])
        result = _filter_empty_comments(df)
        assert len(result) == 2
        assert result["comment-id"].to_list() == ["1", "4"]
