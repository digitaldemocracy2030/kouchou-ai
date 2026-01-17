"""Config JSON file validator."""

import sys
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from schemas.config_schema import PipelineConfig, validate_config_json


class ConfigValidator:
    """Validator for config JSON files."""

    def __init__(self, config_path: str):
        """Initialize validator.

        Args:
            config_path: Path to config JSON file
        """
        self.config_path = config_path
        self.config: PipelineConfig | None = None
        self.errors: list[str] = []

    def validate(self) -> bool:
        """Validate the config JSON file.

        Returns:
            True if valid, False otherwise
        """
        result = validate_config_json(self.config_path)
        self.config = result["config"]
        self.errors = result["errors"]
        return result["valid"]

    def get_validation_report(self) -> dict[str, Any]:
        """Get detailed validation report.

        Returns:
            Dictionary with validation details
        """
        if self.config is None:
            return {"valid": False, "config_path": self.config_path, "errors": self.errors, "config": None}

        return {
            "valid": True,
            "config_path": self.config_path,
            "errors": [],
            "config": {
                "name": self.config.name,
                "question": self.config.question,
                "input": self.config.input,
                "model": self.config.model,
                "provider": self.config.provider,
                "extraction": {
                    "limit": self.config.extraction.limit,
                    "workers": self.config.extraction.workers,
                    "properties": self.config.extraction.properties,
                },
                "hierarchical_clustering": {
                    "cluster_nums": self.config.hierarchical_clustering.cluster_nums,
                },
            },
        }

    @staticmethod
    def validate_file(config_path: str) -> dict[str, Any]:
        """Validate a config file and return report.

        Args:
            config_path: Path to config JSON file

        Returns:
            Validation report dictionary
        """
        validator = ConfigValidator(config_path)
        validator.validate()
        return validator.get_validation_report()


def validate_config_file(config_path: str) -> None:
    """Validate config JSON file and print results.

    Args:
        config_path: Path to config JSON file

    Raises:
        SystemExit: If validation fails
    """
    print(f"Validating config JSON: {config_path}")
    print()

    validator = ConfigValidator(config_path)
    is_valid = validator.validate()
    report = validator.get_validation_report()

    if is_valid:
        print("✓ Config JSON is valid")
        config = report["config"]
        print(f"  - Name: {config['name']}")
        print(f"  - Question: {config['question']}")
        print(f"  - Input: {config['input']}")
        print(f"  - Model: {config['model']}")
        if config["provider"]:
            print(f"  - Provider: {config['provider']}")
        print(f"  - Extraction limit: {config['extraction']['limit']}")
        print(f"  - Extraction workers: {config['extraction']['workers']}")
        if config["extraction"]["properties"]:
            print(f"  - Properties: {', '.join(config['extraction']['properties'])}")
        print(f"  - Cluster numbers: {config['hierarchical_clustering']['cluster_nums']}")
    else:
        print("✗ Config JSON is invalid")
        print("Errors:")
        for error in report["errors"]:
            print(f"  - {error}")
        sys.exit(1)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Validate config JSON file")
    parser.add_argument("config_path", help="Path to config JSON file")
    args = parser.parse_args()

    validate_config_file(args.config_path)
