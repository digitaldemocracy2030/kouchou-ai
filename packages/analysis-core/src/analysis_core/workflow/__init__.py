"""
Workflow module for defining and executing analysis pipelines.

This module provides the infrastructure for defining workflows as a sequence
of steps with dependencies, and executing them in the correct order.

Example:
    from analysis_core.workflow import (
        WorkflowDefinition,
        WorkflowStep,
        WorkflowEngine,
    )

    # Define a workflow
    workflow = WorkflowDefinition(
        id="my-analysis",
        version="1.0.0",
        steps=[
            WorkflowStep(id="extract", plugin="analysis.extraction"),
            WorkflowStep(id="embed", plugin="analysis.embedding", depends_on=["extract"]),
            WorkflowStep(id="cluster", plugin="analysis.hierarchical_clustering", depends_on=["embed"]),
        ],
    )

    # Execute
    engine = WorkflowEngine()
    result = engine.run(workflow, config, ctx)
"""

from analysis_core.workflow.definition import (
    StepResult,
    WorkflowDefinition,
    WorkflowResult,
    WorkflowStep,
)
from analysis_core.workflow.engine import WorkflowEngine, WorkflowExecutionError
from analysis_core.workflow.resolver import (
    CyclicDependencyError,
    DependencyError,
    MissingDependencyError,
    evaluate_condition,
    resolve_execution_order,
    validate_dependencies,
)

__all__ = [
    # Definition
    "WorkflowDefinition",
    "WorkflowStep",
    "WorkflowResult",
    "StepResult",
    # Engine
    "WorkflowEngine",
    "WorkflowExecutionError",
    # Resolver
    "DependencyError",
    "CyclicDependencyError",
    "MissingDependencyError",
    "resolve_execution_order",
    "validate_dependencies",
    "evaluate_condition",
]
