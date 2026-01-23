"""
Pipeline orchestration.

This module provides the main pipeline execution logic,
handling step sequencing, status tracking, and error handling.
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from analysis_core.core.orchestration import (
    initialization,
    run_step,
    termination,
)
from analysis_core.steps import (
    embedding,
    extraction,
    hierarchical_aggregation,
    hierarchical_clustering,
    hierarchical_initial_labelling,
    hierarchical_merge_labelling,
    hierarchical_overview,
    hierarchical_visualization,
)


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
    output_dir: Path | None = None


# Default step functions mapping
DEFAULT_STEP_FUNCTIONS: dict[str, Callable[[dict[str, Any]], None]] = {
    "extraction": extraction,
    "embedding": embedding,
    "hierarchical_clustering": hierarchical_clustering,
    "hierarchical_initial_labelling": hierarchical_initial_labelling,
    "hierarchical_merge_labelling": hierarchical_merge_labelling,
    "hierarchical_overview": hierarchical_overview,
    "hierarchical_aggregation": hierarchical_aggregation,
    "hierarchical_visualization": hierarchical_visualization,
}


class PipelineOrchestrator:
    """
    Orchestrates the execution of analysis pipeline steps.

    This class manages:
    - Step sequencing and dependency resolution
    - Status tracking and persistence
    - Error handling and recovery
    - Token usage accumulation

    Usage:
        # From config file
        orchestrator = PipelineOrchestrator.from_config("config.json")
        result = orchestrator.run()

        # From config dict
        orchestrator = PipelineOrchestrator(config_dict)
        result = orchestrator.run()
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
        output_base_dir: Path | None = None,
        input_base_dir: Path | None = None,
        steps: list[str] | None = None,
    ):
        """
        Initialize the pipeline orchestrator.

        Args:
            config: Pipeline configuration dictionary (already initialized)
            output_base_dir: Base directory for outputs
            input_base_dir: Base directory for inputs
            steps: List of step names to execute (default: all steps)
        """
        self.config = config
        self.output_base_dir = output_base_dir or Path(config.get("_output_base_dir", "outputs"))
        self.input_base_dir = input_base_dir or Path(config.get("_input_base_dir", "inputs"))
        self.steps = steps or self.DEFAULT_STEPS
        self._step_functions: dict[str, Callable] = DEFAULT_STEP_FUNCTIONS.copy()

    @classmethod
    def from_config(
        cls,
        config_path: Path | str,
        force: bool = False,
        only: str | None = None,
        skip_interaction: bool = True,
        without_html: bool = True,
        output_base_dir: Path | None = None,
        input_base_dir: Path | None = None,
    ) -> "PipelineOrchestrator":
        """
        Create an orchestrator from a config file.

        This method handles initialization including:
        - Loading and validating config
        - Setting up step defaults
        - Creating output directories
        - Checking previous run status

        Args:
            config_path: Path to config JSON file
            force: Force re-run all steps
            only: Run only specified step
            skip_interaction: Skip interactive prompts
            without_html: Skip HTML visualization
            output_base_dir: Base directory for outputs
            input_base_dir: Base directory for inputs

        Returns:
            Initialized PipelineOrchestrator
        """
        from analysis_core import steps as steps_module

        config = initialization(
            config_path=config_path,
            force=force,
            only=only,
            skip_interaction=skip_interaction,
            without_html=without_html,
            output_base_dir=output_base_dir,
            input_base_dir=input_base_dir,
            steps_module=steps_module,
        )

        return cls(
            config=config,
            output_base_dir=output_base_dir,
            input_base_dir=input_base_dir,
        )

    def register_step(self, name: str, func: Callable[[dict[str, Any]], None]) -> None:
        """
        Register a custom step function.

        Args:
            name: Step name
            func: Step function that takes config and performs the step
        """
        self._step_functions[name] = func

    def run(self) -> PipelineResult:
        """
        Execute the pipeline.

        Returns:
            PipelineResult with execution details
        """
        start_time = datetime.now()
        step_results: list[StepResult] = []
        error: Exception | None = None

        try:
            # Execute each step
            for step_name in self.steps:
                step_func = self._step_functions.get(step_name)
                if step_func is None:
                    raise ValueError(f"No function registered for step '{step_name}'")

                step_start = datetime.now()
                try:
                    run_step(
                        step=step_name,
                        func=step_func,
                        config=self.config,
                        output_base_dir=self.output_base_dir,
                    )
                    step_duration = (datetime.now() - step_start).total_seconds()
                    step_results.append(StepResult(
                        step_name=step_name,
                        success=True,
                        duration_seconds=step_duration,
                        token_usage=self.config.get("total_token_usage", 0),
                    ))
                except Exception as e:
                    step_duration = (datetime.now() - step_start).total_seconds()
                    step_results.append(StepResult(
                        step_name=step_name,
                        success=False,
                        duration_seconds=step_duration,
                        error=str(e),
                    ))
                    raise

            # Finalize successfully
            termination(self.config, error=None, output_base_dir=self.output_base_dir)

        except Exception as e:
            error = e
            try:
                termination(self.config, error=e, output_base_dir=self.output_base_dir)
            except Exception:
                pass  # termination re-raises, we catch it here

        total_duration = (datetime.now() - start_time).total_seconds()
        output_path = self.output_base_dir / self.config.get("output_dir", "")

        return PipelineResult(
            success=error is None,
            steps=step_results,
            total_duration_seconds=total_duration,
            total_token_usage=self.config.get("total_token_usage", 0),
            error=str(error) if error else None,
            output_dir=output_path if output_path.exists() else None,
        )

    def get_status(self) -> dict[str, Any]:
        """Get current pipeline status from config."""
        return {
            "status": self.config.get("status"),
            "current_job": self.config.get("current_job"),
            "completed_jobs": self.config.get("completed_jobs", []),
            "total_token_usage": self.config.get("total_token_usage", 0),
            "plan": self.config.get("plan", []),
        }

    def get_plan(self) -> list[dict[str, Any]]:
        """Get the execution plan."""
        return self.config.get("plan", [])

    @classmethod
    def from_dict(
        cls,
        config: dict[str, Any],
        output_dir: str | None = None,
        output_base_dir: Path | str | None = None,
        input_base_dir: Path | str | None = None,
    ) -> "PipelineOrchestrator":
        """
        Create an orchestrator from a configuration dictionary.

        This is a simpler alternative to from_config() that doesn't require
        a config file and uses default prompts and settings.

        Args:
            config: Pipeline configuration dictionary
            output_dir: Output directory name (defaults to config["name"])
            output_base_dir: Base directory for outputs (default: outputs/)
            input_base_dir: Base directory for inputs (default: inputs/)

        Returns:
            Initialized PipelineOrchestrator
        """
        from analysis_core.compat import normalize_config

        # Normalize config with defaults
        normalized = normalize_config(config.copy())

        # Set output directory
        normalized["output_dir"] = output_dir or config.get("name", "analysis")

        # Convert paths
        output_base = Path(output_base_dir) if output_base_dir else Path("outputs")
        input_base = Path(input_base_dir) if input_base_dir else Path("inputs")

        normalized["_output_base_dir"] = str(output_base)
        normalized["_input_base_dir"] = str(input_base)

        # Create output directory
        output_path = output_base / normalized["output_dir"]
        output_path.mkdir(parents=True, exist_ok=True)

        # Create a simple plan (all steps run)
        normalized["plan"] = [
            {"step": step, "run": True, "reason": "new run"}
            for step in cls.DEFAULT_STEPS
        ]

        # Skip visualization if requested
        if normalized.get("without_html", True):
            for plan_step in normalized["plan"]:
                if plan_step["step"] == "hierarchical_visualization":
                    plan_step["run"] = False
                    plan_step["reason"] = "skipping html output"

        return cls(
            config=normalized,
            output_base_dir=output_base,
            input_base_dir=input_base,
        )

    def run_workflow(self) -> "PipelineResult":
        """
        Execute the pipeline using the workflow engine.

        This is an alternative to run() that uses the plugin-based
        workflow engine instead of direct step function calls.

        Returns:
            PipelineResult with execution details
        """
        from analysis_core.compat import create_step_context_from_config
        from analysis_core.workflow import WorkflowEngine
        from analysis_core.workflows import HIERARCHICAL_DEFAULT_WORKFLOW

        start_time = datetime.now()

        try:
            # Create step context
            ctx = create_step_context_from_config(
                self.config,
                output_dir=self.config.get("output_dir"),
                input_dir=str(self.input_base_dir),
                output_base_dir=str(self.output_base_dir),
            )

            # Run workflow
            engine = WorkflowEngine()
            workflow_result = engine.run(
                HIERARCHICAL_DEFAULT_WORKFLOW,
                self.config,
                ctx,
            )

            # Convert to PipelineResult
            step_results = [
                StepResult(
                    step_name=step_id,
                    success=result.success,
                    duration_seconds=0.0,  # Not tracked in workflow mode
                    token_usage=result.outputs.token_usage if result.outputs else 0,
                    error=result.error,
                )
                for step_id, result in workflow_result.step_results.items()
            ]

            total_duration = (datetime.now() - start_time).total_seconds()
            output_path = self.output_base_dir / self.config.get("output_dir", "")

            return PipelineResult(
                success=workflow_result.success,
                steps=step_results,
                total_duration_seconds=total_duration,
                total_token_usage=workflow_result.total_token_usage,
                error=None,
                output_dir=output_path if output_path.exists() else None,
            )

        except Exception as e:
            total_duration = (datetime.now() - start_time).total_seconds()
            return PipelineResult(
                success=False,
                steps=[],
                total_duration_seconds=total_duration,
                total_token_usage=0,
                error=str(e),
                output_dir=None,
            )
