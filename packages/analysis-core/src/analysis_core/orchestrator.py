"""
Pipeline orchestration.

This module provides the main pipeline execution logic,
handling step sequencing, status tracking, and error handling.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable
import json
from datetime import datetime


@dataclass
class StepResult:
    """Result of a pipeline step execution."""

    step_name: str
    success: bool
    duration_seconds: float
    token_usage: int = 0
    error: str | None = None


@dataclass
class PipelineResult:
    """Result of a complete pipeline execution."""

    success: bool
    steps: list[StepResult] = field(default_factory=list)
    total_duration_seconds: float = 0.0
    total_token_usage: int = 0
    error: str | None = None


class PipelineOrchestrator:
    """
    Orchestrates the execution of analysis pipeline steps.

    This class manages:
    - Step sequencing and dependency resolution
    - Status tracking and persistence
    - Error handling and recovery
    - Token usage accumulation
    """

    # Default step sequence for hierarchical analysis
    DEFAULT_STEPS = [
        "extraction",
        "embedding",
        "hierarchical_clustering",
        "hierarchical_initial_labelling",
        "hierarchical_merge_labelling",
        "hierarchical_overview",
        "hierarchical_aggregation",
        "hierarchical_visualization",
    ]

    def __init__(
        self,
        config: dict[str, Any],
        output_dir: Path | None = None,
        steps: list[str] | None = None,
    ):
        """
        Initialize the pipeline orchestrator.

        Args:
            config: Pipeline configuration dictionary
            output_dir: Output directory for results
            steps: List of step names to execute (default: all steps)
        """
        self.config = config
        self.output_dir = output_dir or Path(config.get("output_dir", "outputs"))
        self.steps = steps or self.DEFAULT_STEPS
        self._step_functions: dict[str, Callable] = {}
        self._status: dict[str, Any] = {}

    def register_step(self, name: str, func: Callable) -> None:
        """Register a step function."""
        self._step_functions[name] = func

    def run(
        self,
        force: bool = False,
        only_step: str | None = None,
        skip_html: bool = True,
    ) -> PipelineResult:
        """
        Execute the pipeline.

        Args:
            force: Force re-run all steps
            only_step: Run only a specific step
            skip_html: Skip HTML visualization step

        Returns:
            PipelineResult with execution details
        """
        # TODO: Implement actual pipeline execution
        # For now, this is a stub that returns a placeholder result
        return PipelineResult(
            success=False,
            error="Pipeline execution not yet implemented. Use legacy hierarchical_main.py",
        )

    def get_status(self) -> dict[str, Any]:
        """Get current pipeline status."""
        return self._status.copy()

    def _load_status(self) -> dict[str, Any]:
        """Load status from file."""
        status_file = self.output_dir / "hierarchical_status.json"
        if status_file.exists():
            with open(status_file, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _save_status(self) -> None:
        """Save status to file."""
        status_file = self.output_dir / "hierarchical_status.json"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        with open(status_file, "w", encoding="utf-8") as f:
            json.dump(self._status, f, ensure_ascii=False, indent=2)

    def _decide_what_to_run(self, previous_status: dict[str, Any]) -> list[str]:
        """
        Determine which steps need to be executed.

        Compares current config with previous run to detect changes.
        """
        steps_to_run = []

        # Check each step's dependencies and parameters
        for step in self.steps:
            if self._should_run_step(step, previous_status):
                steps_to_run.append(step)

        return steps_to_run

    def _should_run_step(self, step: str, previous_status: dict[str, Any]) -> bool:
        """Check if a step should be run based on previous status and config changes."""
        # If step wasn't completed before, run it
        completed_jobs = previous_status.get("completed_jobs", [])
        step_completed = any(job.get("step") == step for job in completed_jobs)

        if not step_completed:
            return True

        # Check if parameters changed
        # TODO: Implement parameter change detection

        return False
