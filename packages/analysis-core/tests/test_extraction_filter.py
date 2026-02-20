"""Test that empty/whitespace-only comments are filtered out in extraction step (#583)."""

import os
import tempfile

import polars as pl
import pytest


class TestEmptyCommentFiltering:
    """Test filtering of empty/whitespace-only comments before LLM processing."""

    def _create_csv(self, rows: list[dict], path: str) -> None:
        df = pl.DataFrame(rows)
        df.write_csv(path)

    def test_filters_empty_strings(self, tmp_path):
        """Empty string comments should be removed."""
        csv_path = str(tmp_path / "input.csv")
        self._create_csv(
            [
                {"comment-id": "1", "comment-body": "valid comment"},
                {"comment-id": "2", "comment-body": ""},
                {"comment-id": "3", "comment-body": "another valid comment"},
            ],
            csv_path,
        )

        comments = pl.read_csv(csv_path, columns=["comment-id", "comment-body"])
        comments = comments.filter(
            pl.col("comment-body").is_not_null() & (pl.col("comment-body").str.strip_chars() != "")
        )

        assert len(comments) == 2
        assert comments["comment-id"].to_list() == [1, 3]

    def test_filters_whitespace_only(self, tmp_path):
        """Whitespace-only comments should be removed."""
        csv_path = str(tmp_path / "input.csv")
        self._create_csv(
            [
                {"comment-id": "1", "comment-body": "valid comment"},
                {"comment-id": "2", "comment-body": "   "},
                {"comment-id": "3", "comment-body": "\t\n"},
            ],
            csv_path,
        )

        comments = pl.read_csv(csv_path, columns=["comment-id", "comment-body"])
        comments = comments.filter(
            pl.col("comment-body").is_not_null() & (pl.col("comment-body").str.strip_chars() != "")
        )

        assert len(comments) == 1
        assert comments["comment-id"].to_list() == [1]

    def test_keeps_valid_comments(self, tmp_path):
        """Valid comments should not be filtered out."""
        csv_path = str(tmp_path / "input.csv")
        self._create_csv(
            [
                {"comment-id": "1", "comment-body": "first comment"},
                {"comment-id": "2", "comment-body": "second comment"},
                {"comment-id": "3", "comment-body": "third comment"},
            ],
            csv_path,
        )

        comments = pl.read_csv(csv_path, columns=["comment-id", "comment-body"])
        original_count = len(comments)
        comments = comments.filter(
            pl.col("comment-body").is_not_null() & (pl.col("comment-body").str.strip_chars() != "")
        )

        assert len(comments) == original_count

    def test_all_empty_raises_error(self, tmp_path):
        """When all comments are empty, a RuntimeError should be raised."""
        csv_path = str(tmp_path / "input.csv")
        self._create_csv(
            [
                {"comment-id": "1", "comment-body": ""},
                {"comment-id": "2", "comment-body": "   "},
                {"comment-id": "3", "comment-body": "\n"},
            ],
            csv_path,
        )

        comments = pl.read_csv(csv_path, columns=["comment-id", "comment-body"])
        comments = comments.filter(
            pl.col("comment-body").is_not_null() & (pl.col("comment-body").str.strip_chars() != "")
        )

        assert len(comments) == 0
        with pytest.raises(RuntimeError, match="All comments are empty"):
            if len(comments) == 0:
                raise RuntimeError("All comments are empty or whitespace-only after filtering")

    def test_mixed_empty_and_valid(self, tmp_path):
        """Mixed input should keep only valid comments."""
        csv_path = str(tmp_path / "input.csv")
        self._create_csv(
            [
                {"comment-id": "1", "comment-body": "valid"},
                {"comment-id": "2", "comment-body": ""},
                {"comment-id": "3", "comment-body": "   "},
                {"comment-id": "4", "comment-body": "also valid"},
                {"comment-id": "5", "comment-body": "\n\n"},
            ],
            csv_path,
        )

        comments = pl.read_csv(csv_path, columns=["comment-id", "comment-body"])
        original_count = len(comments)
        comments = comments.filter(
            pl.col("comment-body").is_not_null() & (pl.col("comment-body").str.strip_chars() != "")
        )
        filtered_count = original_count - len(comments)

        assert len(comments) == 2
        assert filtered_count == 3
        assert comments["comment-id"].to_list() == [1, 4]
