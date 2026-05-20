"""
Pipeline orchestration.

This module provides the main pipeline execution logic,
handling step sequencing, status tracking, and error handling.
"""

import json
import traceback
import warnings
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable

from analysis_core.core.orchestration import (
    initialization,
    run_step,
    sync_without_html_keys,
    termination,
    update_status,
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
        result = orchestrator.run_default()

        # From config dict
        orchestrator = PipelineOrchestrator(config_dict)
        result = orchestrator.run_default()
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
        validate_api_keys_early: bool = True,
        persist_status: bool = True,
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
            validate_api_keys_early: Validate provider credentials during initialization
            persist_status: Persist running/completed status to hierarchical_status.json
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
            validate_api_keys_early=validate_api_keys_early,
            persist_status=persist_status,
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
        Execute the legacy direct-step pipeline.

        Returns:
            PipelineResult with execution details
        """
        warnings.warn(
            "PipelineOrchestrator.run() is deprecated; use run_default() for the canonical workflow path.",
            DeprecationWarning,
            stacklevel=2,
        )
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
                    step_results.append(
                        StepResult(
                            step_name=step_name,
                            success=True,
                            duration_seconds=step_duration,
                            token_usage=self.config.get("total_token_usage", 0),
                        )
                    )
                except Exception as e:
                    step_duration = (datetime.now() - step_start).total_seconds()
                    step_results.append(
                        StepResult(
                            step_name=step_name,
                            success=False,
                            duration_seconds=step_duration,
                            error=str(e),
                        )
                    )
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

    def run_default(self) -> PipelineResult:
        """Execute the default pipeline path used by the CLI."""
        return self.run_workflow()

    def _carry_forward_previous_jobs(self) -> None:
        """Preserve older completed jobs across reruns."""
        if "previous" not in self.config:
            return

        old_jobs = self.config["previous"].get("completed_jobs", []) + self.config["previous"].get(
            "previously_completed_jobs", []
        )
        newly_completed = [job["step"] for job in self.config.get("completed_jobs", [])]
        self.config["previously_completed_jobs"] = [job for job in old_jobs if job["step"] not in newly_completed]
        del self.config["previous"]

    @staticmethod
    def _extract_workflow_error(workflow_result: Any) -> str:
        """Return the most specific error available from a workflow result."""
        for step_id, result in workflow_result.step_results.items():
            if not result.success and result.error:
                return result.error
        return "Workflow execution failed"

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
        from analysis_core.core.orchestration import _PACKAGE_DIR, decide_what_to_run, load_specs, validate_api_keys

        # Normalize config with defaults
        normalized = normalize_config(config.copy())

        # Validate API keys early (fail-fast)
        provider = normalized.get("provider", "openai")
        user_api_key = normalized.get("user_api_key")
        validate_api_keys(provider, user_api_key)

        # Set output directory
        normalized["output_dir"] = output_dir or config.get("name", "analysis")

        # Convert paths
        output_base = Path(output_base_dir) if output_base_dir else Path("outputs")
        input_base = Path(input_base_dir) if input_base_dir else Path("inputs")

        normalized["_output_base_dir"] = str(output_base)
        normalized["_input_base_dir"] = str(input_base)
        sync_without_html_keys(normalized)

        # Create output directory
        output_path = output_base / normalized["output_dir"]
        output_path.mkdir(parents=True, exist_ok=True)

        status_file = output_path / "hierarchical_status.json"
        previous: dict[str, Any] | None = None
        if status_file.exists():
            previous = json.loads(status_file.read_text(encoding="utf-8"))
            normalized["previous"] = previous

        specs = load_specs(_PACKAGE_DIR / "specs" / "hierarchical_specs.json")
        if "plan" in config:
            normalized["plan"] = config["plan"]
        else:
            normalized["plan"] = decide_what_to_run(normalized, previous, specs, output_base)

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
        from analysis_core.workflow.definition import StepResult as WorkflowStepResult
        from analysis_core.workflows import HIERARCHICAL_DEFAULT_WORKFLOW

        start_time = datetime.now()
        workflow = HIERARCHICAL_DEFAULT_WORKFLOW
        plan_step_to_workflow_step = {
            "extraction": "extraction",
            "embedding": "embedding",
            "hierarchical_clustering": "clustering",
            "hierarchical_initial_labelling": "initial_labelling",
            "hierarchical_merge_labelling": "merge_labelling",
            "hierarchical_overview": "overview",
            "hierarchical_aggregation": "aggregation",
            "hierarchical_visualization": "visualization",
        }
        workflow_step_to_plan_step = {v: k for k, v in plan_step_to_workflow_step.items()}
        skip_steps = {
            plan_step_to_workflow_step[step["step"]]
            for step in self.config.get("plan", [])
            if not step.get("run", True) and step["step"] in plan_step_to_workflow_step
        }

        def workflow_step_to_legacy_name(step_name: str) -> str:
            return workflow_step_to_plan_step.get(step_name, step_name)

        def mark_step_started(step_name: str) -> None:
            update_status(
                self.config,
                {
                    "current_job": workflow_step_to_legacy_name(step_name),
                    "current_job_started": datetime.now().isoformat(),
                },
                self.output_base_dir,
            )

        def mark_step_completed(step_name: str, result: WorkflowStepResult) -> None:
            legacy_step_name = workflow_step_to_legacy_name(step_name)
            completed_jobs = self.config.get("completed_jobs", []).copy()
            total_token_usage = self.config.get("total_token_usage", 0)
            token_usage_input = self.config.get("token_usage_input", 0)
            token_usage_output = self.config.get("token_usage_output", 0)
            if result.success and not result.skipped:
                step_token_usage = result.outputs.token_usage if result.outputs else 0
                step_token_input = result.outputs.token_input if result.outputs else 0
                step_token_output = result.outputs.token_output if result.outputs else 0
                completed_jobs.append(
                    {
                        "step": legacy_step_name,
                        "completed": datetime.now().isoformat(),
                        "duration": 0.0,
                        "params": self.config.get(legacy_step_name, {}),
                        "token_usage": step_token_usage,
                    }
                )
                total_token_usage += step_token_usage
                token_usage_input += step_token_input
                token_usage_output += step_token_output

            update_status(
                self.config,
                {
                    "current_job": legacy_step_name,
                    "current_job_progress": None,
                    "current_jop_tasks": None,
                    "completed_jobs": completed_jobs,
                    "total_token_usage": total_token_usage,
                    "token_usage_input": token_usage_input,
                    "token_usage_output": token_usage_output,
                },
                self.output_base_dir,
            )

        try:
            # Create step context
            ctx = create_step_context_from_config(
                self.config,
                output_dir=self.config.get("output_dir"),
                input_dir=str(self.input_base_dir),
                output_base_dir=str(self.output_base_dir),
            )

            update_status(
                self.config,
                {
                    "plan": self.config.get("plan", []),
                    "status": "running",
                    "start_time": start_time.isoformat(),
                    "completed_jobs": [],
                    "total_token_usage": 0,
                    "token_usage_input": 0,
                    "token_usage_output": 0,
                    "provider": self.config.get("provider"),
                    "model": self.config.get("model"),
                },
                self.output_base_dir,
            )

            # Run workflow
            engine = WorkflowEngine()
            workflow_result = engine.run(
                workflow,
                self.config,
                ctx,
                on_step_start=mark_step_started,
                on_step_complete=mark_step_completed,
                skip_steps=skip_steps,
            )

            self.config["total_token_usage"] = workflow_result.total_token_usage
            self.config["token_usage_input"] = workflow_result.total_token_input
            self.config["token_usage_output"] = workflow_result.total_token_output

            # Convert to PipelineResult
            step_results = [
                StepResult(
                    step_name=workflow_step_to_legacy_name(step_id),
                    success=result.success,
                    duration_seconds=0.0,  # Not tracked in workflow mode
                    token_usage=result.outputs.token_usage if result.outputs else 0,
                    error=result.error,
                )
                for step_id, result in workflow_result.step_results.items()
            ]

            total_duration = (datetime.now() - start_time).total_seconds()
            output_path = self.output_base_dir / self.config.get("output_dir", "")

            self._carry_forward_previous_jobs()

            workflow_error = self._extract_workflow_error(workflow_result)

            update_status(
                self.config,
                {
                    "status": "completed" if workflow_result.success else "error",
                    "end_time": datetime.now().isoformat(),
                    "total_token_usage": workflow_result.total_token_usage,
                    "token_usage_input": workflow_result.total_token_input,
                    "token_usage_output": workflow_result.total_token_output,
                    "error": None if workflow_result.success else workflow_error,
                },
                self.output_base_dir,
            )

            return PipelineResult(
                success=workflow_result.success,
                steps=step_results,
                total_duration_seconds=total_duration,
                total_token_usage=workflow_result.total_token_usage,
                error=None if workflow_result.success else workflow_error,
                output_dir=output_path if output_path.exists() else None,
            )

        except Exception as e:
            total_duration = (datetime.now() - start_time).total_seconds()
            self._carry_forward_previous_jobs()
            update_status(
                self.config,
                {
                    "status": "error",
                    "end_time": datetime.now().isoformat(),
                    "error": str(e),
                    "error_stack_trace": traceback.format_exc(),
                },
                self.output_base_dir,
            )
            return PipelineResult(
                success=False,
                steps=[],
                total_duration_seconds=total_duration,
                total_token_usage=self.config.get("total_token_usage", 0),
                error=str(e),
                output_dir=None,
            )
