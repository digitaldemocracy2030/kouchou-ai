"""Output JSON file validator."""

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from schemas.output_schema import (
    HierarchicalResultSchema,
    StatusSchema,
    validate_output_json,
    validate_status_json,
)


class OutputValidator:
    """Validator for output JSON files."""

    def __init__(self, output_dir: str):
        """Initialize validator.

        Args:
            output_dir: Path to output directory
        """
        self.output_dir = Path(output_dir)
        self.result_schema: HierarchicalResultSchema | None = None
        self.status_schema: StatusSchema | None = None
        self.errors: list[str] = []

    def validate_result(self) -> bool:
        """Validate the hierarchical_result.json file.

        Returns:
            True if valid, False otherwise
        """
        result_path = self.output_dir / "hierarchical_result.json"
        result = validate_output_json(str(result_path))
        self.result_schema = result["output"]
        if not result["valid"]:
            self.errors.extend(result["errors"])
        return result["valid"]

    def validate_status(self) -> bool:
        """Validate the hierarchical_status.json file.

        Returns:
            True if valid, False otherwise
        """
        status_path = self.output_dir / "hierarchical_status.json"
        result = validate_status_json(str(status_path))
        self.status_schema = result["status"]
        if not result["valid"]:
            self.errors.extend(result["errors"])
        return result["valid"]

    def validate_all(self) -> bool:
        """Validate all output files.

        Returns:
            True if all valid, False otherwise
        """
        result_valid = self.validate_result()
        status_valid = self.validate_status()
        return result_valid and status_valid

    def check_required_files(self) -> dict[str, bool]:
        """Check if all required output files exist.

        Returns:
            Dictionary mapping filename to existence status
        """
        required_files = [
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

        return {filename: (self.output_dir / filename).exists() for filename in required_files}

    def get_validation_report(self) -> dict[str, Any]:
        """Get detailed validation report.

        Returns:
            Dictionary with validation details
        """
        file_status = self.check_required_files()

        report: dict[str, Any] = {
            "output_dir": str(self.output_dir),
            "errors": self.errors,
            "files": file_status,
            "all_files_exist": all(file_status.values()),
        }

        if self.result_schema:
            report["result"] = {
                "arguments_count": len(self.result_schema.arguments),
                "clusters_count": len(self.result_schema.clusters),
                "has_intro": self.result_schema.intro is not None,
                "has_overview": self.result_schema.overview is not None,
            }

        if self.status_schema:
            report["status"] = {
                "status": self.status_schema.status,
                "total_token_usage": self.status_schema.total_token_usage,
                "estimated_cost": self.status_schema.estimated_cost,
                "completed_jobs_count": len(self.status_schema.completed_jobs),
            }

        return report

    @staticmethod
    def validate_directory(output_dir: str) -> dict[str, Any]:
        """Validate an output directory and return report.

        Args:
            output_dir: Path to output directory

        Returns:
            Validation report dictionary
        """
        validator = OutputValidator(output_dir)
        validator.validate_all()
        return validator.get_validation_report()


def validate_output_directory(output_dir: str) -> None:
    """Validate output directory and print results.

    Args:
        output_dir: Path to output directory

    Raises:
        SystemExit: If validation fails
    """
    print(f"Validating output directory: {output_dir}")
    print()

    validator = OutputValidator(output_dir)
    result_valid = validator.validate_result()
    status_valid = validator.validate_status()
    report = validator.get_validation_report()

    print("File existence check:")
    for filename, exists in report["files"].items():
        status = "✓" if exists else "✗"
        print(f"  {status} {filename}")
    print()

    if result_valid:
        print("✓ hierarchical_result.json is valid")
        if "result" in report:
            print(f"  - Arguments: {report['result']['arguments_count']}")
            print(f"  - Clusters: {report['result']['clusters_count']}")
            print(f"  - Has intro: {report['result']['has_intro']}")
            print(f"  - Has overview: {report['result']['has_overview']}")
    else:
        print("✗ hierarchical_result.json is invalid")

    print()

    if status_valid:
        print("✓ hierarchical_status.json is valid")
        if "status" in report:
            print(f"  - Status: {report['status']['status']}")
            print(f"  - Total tokens: {report['status']['total_token_usage']}")
            print(f"  - Estimated cost: ${report['status']['estimated_cost']:.4f}")
            print(f"  - Completed jobs: {report['status']['completed_jobs_count']}")
    else:
        print("✗ hierarchical_status.json is invalid")

    if report["errors"]:
        print()
        print("Errors:")
        for error in report["errors"]:
            print(f"  - {error}")

    if not (result_valid and status_valid and report["all_files_exist"]):
        sys.exit(1)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Validate output directory")
    parser.add_argument("output_dir", help="Path to output directory")
    args = parser.parse_args()

    validate_output_directory(args.output_dir)
