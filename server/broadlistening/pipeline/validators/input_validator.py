"""Input CSV file validator."""

import sys
from pathlib import Path
from typing import Any

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from schemas.input_csv_schema import InputCSVSchema, validate_input_csv


class InputValidator:
    """Validator for input CSV files."""

    def __init__(self, csv_path: str, required_properties: list[str] | None = None):
        """Initialize validator.

        Args:
            csv_path: Path to CSV file
            required_properties: List of required property columns
        """
        self.csv_path = csv_path
        self.required_properties = required_properties or []
        self.schema: InputCSVSchema | None = None
        self.errors: list[str] = []

    def validate(self) -> bool:
        """Validate the input CSV file.

        Returns:
            True if valid, False otherwise
        """
        result = validate_input_csv(self.csv_path, self.required_properties)
        self.schema = result["schema"]
        self.errors = result["errors"]
        return result["valid"]

    def get_validation_report(self) -> dict[str, Any]:
        """Get detailed validation report.

        Returns:
            Dictionary with validation details
        """
        if self.schema is None:
            return {
                "valid": False,
                "csv_path": self.csv_path,
                "errors": self.errors,
                "row_count": 0,
                "columns": [],
            }

        return {
            "valid": True,
            "csv_path": self.csv_path,
            "errors": [],
            "row_count": len(self.schema.rows),
            "columns": ["comment-id", "comment-body"] + self.schema.additional_properties,
            "required_properties": self.required_properties,
            "additional_properties": self.schema.additional_properties,
        }

    @staticmethod
    def validate_file(csv_path: str, required_properties: list[str] | None = None) -> dict[str, Any]:
        """Validate a CSV file and return report.

        Args:
            csv_path: Path to CSV file
            required_properties: List of required property columns

        Returns:
            Validation report dictionary
        """
        validator = InputValidator(csv_path, required_properties)
        validator.validate()
        return validator.get_validation_report()


def validate_input_file(csv_path: str, required_properties: list[str] | None = None) -> None:
    """Validate input CSV file and print results.

    Args:
        csv_path: Path to CSV file
        required_properties: List of required property columns

    Raises:
        SystemExit: If validation fails
    """
    print(f"Validating input CSV: {csv_path}")
    print(f"Required properties: {required_properties or 'None'}")
    print()

    validator = InputValidator(csv_path, required_properties)
    is_valid = validator.validate()
    report = validator.get_validation_report()

    if is_valid:
        print("✓ Input CSV is valid")
        print(f"  - Rows: {report['row_count']}")
        print(f"  - Columns: {', '.join(report['columns'])}")
        if report['additional_properties']:
            print(f"  - Additional properties: {', '.join(report['additional_properties'])}")
    else:
        print("✗ Input CSV is invalid")
        print("Errors:")
        for error in report["errors"]:
            print(f"  - {error}")
        sys.exit(1)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Validate input CSV file")
    parser.add_argument("csv_path", help="Path to CSV file")
    parser.add_argument("--properties", nargs="*", help="Required property columns")
    args = parser.parse_args()

    validate_input_file(args.csv_path, args.properties)
