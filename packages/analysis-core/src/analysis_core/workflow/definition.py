"""
Workflow definition models.

This module defines the data structures for representing workflows,
including steps, dependencies, and conditions.
"""

from dataclasses import dataclass, field
from typing import Any


@dataclass
class WorkflowStep:
    """
    A single step in a workflow.

    Attributes:
        id: Unique step identifier within the workflow
        plugin: Plugin ID to execute (e.g., "analysis.extraction")
        config: Step-specific configuration
        depends_on: List of step IDs this step depends on
        optional: Whether this step is optional (can be skipped)
        condition: Optional condition expression for conditional execution
    """

    id: str
    plugin: str
    config: dict[str, Any] = field(default_factory=dict)
    depends_on: list[str] = field(default_factory=list)
    optional: bool = False
    condition: str | None = None


@dataclass
class WorkflowDefinition:
    """
    Complete workflow definition.

    A workflow defines a sequence of steps with their dependencies
    and configurations. The engine executes steps in dependency order.

    Attributes:
        id: Unique workflow identifier
        version: Workflow version
        name: Human-readable name
        description: Workflow description
        steps: List of steps in the workflow
    """

    id: str
    version: str
    name: str = ""
    description: str = ""
    steps: list[WorkflowStep] = field(default_factory=list)

    def get_step(self, step_id: str) -> WorkflowStep | None:
        """Get a step by ID."""
        for step in self.steps:
            if step.id == step_id:
                return step
        return None

    def get_step_ids(self) -> list[str]:
        """Get all step IDs in the workflow."""
        return [step.id for step in self.steps]


@dataclass
class StepResult:
    """
    Result of executing a single step.

    Attributes:
        step_id: ID of the step that was executed
        success: Whether the step completed successfully
        outputs: Step outputs (artifacts and metadata)
        error: Error message if step failed
        skipped: Whether the step was skipped
    """

    step_id: str
    success: bool = True
    outputs: Any = None
    error: str | None = None
    skipped: bool = False


@dataclass
class WorkflowResult:
    """
    Result of executing a complete workflow.

    Attributes:
        workflow_id: ID of the executed workflow
        success: Whether all steps completed successfully
        step_results: Results for each step
        total_token_usage: Total tokens used across all steps
        total_token_input: Total input tokens
        total_token_output: Total output tokens
    """

    workflow_id: str
    success: bool = True
    step_results: dict[str, StepResult] = field(default_factory=dict)
    total_token_usage: int = 0
    total_token_input: int = 0
    total_token_output: int = 0

    def get_artifacts(self) -> dict[str, Any]:
        """Get all artifacts produced by the workflow."""
        artifacts = {}
        for step_id, result in self.step_results.items():
            if result.outputs and hasattr(result.outputs, "artifacts"):
                for artifact_id, path in result.outputs.artifacts.items():
                    artifacts[f"{step_id}.{artifact_id}"] = path
        return artifacts
