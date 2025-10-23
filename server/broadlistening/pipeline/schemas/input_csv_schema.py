"""Schema definition for input CSV validation."""

from typing import Any

import pandas as pd
from pydantic import BaseModel, Field, field_validator


class InputCSVRow(BaseModel):
    """Schema for a single row in the input CSV file."""

    comment_id: int = Field(..., alias="comment-id", description="Unique identifier for the comment")
    comment_body: str = Field(..., alias="comment-body", description="The comment text")

    model_config = {"populate_by_name": True}

    @field_validator("comment_body")
    @classmethod
    def comment_body_not_empty(cls, v: str) -> str:
        """Validate that comment body is not empty."""
        if not v or not v.strip():
            raise ValueError("comment-body must not be empty")
        return v


class InputCSVSchema(BaseModel):
    """Schema for the entire input CSV file."""

    rows: list[InputCSVRow] = Field(..., description="List of comment rows")
    additional_properties: list[str] = Field(
        default_factory=list, description="Additional property columns present in the CSV"
    )

    @classmethod
    def from_dataframe(cls, df: pd.DataFrame, required_properties: list[str] | None = None) -> "InputCSVSchema":
        """Create schema from pandas DataFrame.

        Args:
            df: Input DataFrame
            required_properties: List of required property columns

        Returns:
            InputCSVSchema instance

        Raises:
            ValueError: If required columns are missing
        """
        required_properties = required_properties or []

        required_columns = {"comment-id", "comment-body"}
        missing_columns = required_columns - set(df.columns)
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")

        missing_properties = set(required_properties) - set(df.columns)
        if missing_properties:
            raise ValueError(f"Missing required property columns: {missing_properties}")

        additional_properties = [col for col in df.columns if col not in required_columns]

        rows = []
        for _, row in df.iterrows():
            row_dict = {"comment-id": row["comment-id"], "comment-body": row["comment-body"]}
            rows.append(InputCSVRow(**row_dict))

        return cls(rows=rows, additional_properties=additional_properties)

    @classmethod
    def validate_csv_file(cls, filepath: str, required_properties: list[str] | None = None) -> "InputCSVSchema":
        """Validate a CSV file.

        Args:
            filepath: Path to CSV file
            required_properties: List of required property columns

        Returns:
            InputCSVSchema instance

        Raises:
            ValueError: If validation fails
            FileNotFoundError: If file doesn't exist
        """
        try:
            df = pd.read_csv(filepath)
        except FileNotFoundError as e:
            raise FileNotFoundError(f"CSV file not found: {filepath}") from e
        except Exception as e:
            raise ValueError(f"Failed to read CSV file: {e}") from e

        if df.empty:
            raise ValueError("CSV file is empty")

        return cls.from_dataframe(df, required_properties)


def validate_input_csv(filepath: str, required_properties: list[str] | None = None) -> dict[str, Any]:
    """Validate input CSV file and return validation result.

    Args:
        filepath: Path to CSV file
        required_properties: List of required property columns

    Returns:
        Dictionary with validation results:
        - valid: bool
        - message: str
        - schema: InputCSVSchema or None
        - errors: list of error messages
    """
    try:
        schema = InputCSVSchema.validate_csv_file(filepath, required_properties)
        return {
            "valid": True,
            "message": f"CSV file is valid with {len(schema.rows)} rows",
            "schema": schema,
            "errors": [],
        }
    except Exception as e:
        return {"valid": False, "message": str(e), "schema": None, "errors": [str(e)]}
