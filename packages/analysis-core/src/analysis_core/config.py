"""
Pipeline configuration management.

This module handles loading, validation, and management of pipeline configurations.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class StepConfig:
    """Configuration for a single pipeline step."""

    name: str
    enabled: bool = True
    params: dict[str, Any] = field(default_factory=dict)


@dataclass
class PipelineConfig:
    """Main pipeline configuration."""

    # Input/Output
    input_path: Path
    output_dir: Path

    # Analysis settings
    question: str
    intro: str = ""
    model: str = "gpt-4o-mini"
    provider: str = "openai"

    # Step configurations
    steps: dict[str, StepConfig] = field(default_factory=dict)

    # Runtime state
    status: str = "pending"

    @classmethod
    def from_json(cls, path: Path) -> "PipelineConfig":
        """Load configuration from a JSON file."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        return cls(
            input_path=Path(data.get("input", "")),
            output_dir=Path(data.get("output_dir", "")),
            question=data.get("question", ""),
            intro=data.get("intro", ""),
            model=data.get("model", "gpt-4o-mini"),
            provider=data.get("provider", "openai"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert configuration to a dictionary."""
        return {
            "input": str(self.input_path),
            "output_dir": str(self.output_dir),
            "question": self.question,
            "intro": self.intro,
            "model": self.model,
            "provider": self.provider,
            "status": self.status,
        }


def load_config(path: Path) -> dict[str, Any]:
    """
    Load a legacy configuration file.

    This function maintains compatibility with the existing hierarchical_main.py
    configuration format.
    """
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_config(config: dict[str, Any], path: Path) -> None:
    """Save configuration to a JSON file."""
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
