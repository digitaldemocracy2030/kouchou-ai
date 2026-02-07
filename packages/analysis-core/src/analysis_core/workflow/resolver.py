"""
Dependency resolver for workflows.

This module provides functions for resolving step execution order
based on their dependencies using topological sorting.
"""

from collections import deque
from typing import Any

from analysis_core.workflow.definition import WorkflowDefinition


class DependencyError(Exception):
    """Raised when there is an issue with workflow dependencies."""

    pass


class CyclicDependencyError(DependencyError):
    """Raised when a cyclic dependency is detected in the workflow."""

    pass


class MissingDependencyError(DependencyError):
    """Raised when a step depends on a non-existent step."""

    pass


def validate_dependencies(workflow: WorkflowDefinition) -> list[str]:
    """
    Validate workflow dependencies.

    Checks for:
    - Missing dependencies (referencing non-existent steps)
    - Self-dependencies
    - Cyclic dependencies

    Args:
        workflow: Workflow definition to validate

    Returns:
        List of error messages (empty if valid)
    """
    errors = []
    step_ids = set(workflow.get_step_ids())

    for step in workflow.steps:
        # Check for self-dependency
        if step.id in step.depends_on:
            errors.append(f"Step '{step.id}' depends on itself")

        # Check for missing dependencies
        for dep_id in step.depends_on:
            if dep_id not in step_ids:
                errors.append(f"Step '{step.id}' depends on non-existent step '{dep_id}'")

    # Check for cycles
    try:
        resolve_execution_order(workflow)
    except CyclicDependencyError as e:
        errors.append(str(e))

    return errors


def resolve_execution_order(workflow: WorkflowDefinition) -> list[str]:
    """
    Determine the execution order of steps using topological sort.

    Uses Kahn's algorithm to produce a valid execution order that
    respects all dependencies.

    Args:
        workflow: Workflow definition

    Returns:
        List of step IDs in execution order

    Raises:
        CyclicDependencyError: If the workflow has cyclic dependencies
        MissingDependencyError: If a step depends on a non-existent step
    """
    step_ids = workflow.get_step_ids()
    step_map = {step.id: step for step in workflow.steps}

    # Validate all dependencies exist
    for step in workflow.steps:
        for dep_id in step.depends_on:
            if dep_id not in step_map:
                raise MissingDependencyError(f"Step '{step.id}' depends on non-existent step '{dep_id}'")

    # Build adjacency list and in-degree count
    # in_degree[step_id] = number of steps this step depends on
    in_degree: dict[str, int] = {step_id: 0 for step_id in step_ids}
    # dependents[step_id] = list of steps that depend on this step
    dependents: dict[str, list[str]] = {step_id: [] for step_id in step_ids}

    for step in workflow.steps:
        in_degree[step.id] = len(step.depends_on)
        for dep_id in step.depends_on:
            dependents[dep_id].append(step.id)

    # Initialize queue with steps that have no dependencies
    queue = deque([step_id for step_id, degree in in_degree.items() if degree == 0])
    execution_order = []

    while queue:
        # Process steps with no remaining dependencies
        current = queue.popleft()
        execution_order.append(current)

        # Reduce in-degree of dependent steps
        for dependent_id in dependents[current]:
            in_degree[dependent_id] -= 1
            if in_degree[dependent_id] == 0:
                queue.append(dependent_id)

    # Check if all steps were processed
    if len(execution_order) != len(step_ids):
        # Find steps involved in cycle
        unprocessed = [step_id for step_id in step_ids if step_id not in execution_order]
        raise CyclicDependencyError(f"Cyclic dependency detected involving steps: {unprocessed}")

    return execution_order


def evaluate_condition(
    condition: str | None,
    config: dict[str, Any],
    step_results: dict[str, Any],
) -> bool:
    """
    Evaluate a step condition expression.

    Conditions can reference:
    - config values: ${config.key}
    - step results: ${steps.step_id.success}

    Args:
        condition: Condition expression (or None for always true)
        config: Full workflow configuration
        step_results: Results from previously executed steps

    Returns:
        True if condition is met or no condition specified
    """
    if condition is None:
        return True

    # Simple evaluation - for now just handle common patterns
    # TODO: Implement proper expression evaluation

    # Check for "not config.without_html" pattern
    if condition.strip() == "${not config.without_html}":
        return not config.get("without_html", False)

    # Check for "${config.key}" pattern
    if condition.startswith("${config.") and condition.endswith("}"):
        key = condition[9:-1]  # Extract key from ${config.key}
        return bool(config.get(key, False))

    # Default to true for unrecognized conditions
    return True
