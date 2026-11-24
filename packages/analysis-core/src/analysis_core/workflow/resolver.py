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


class DuplicateStepError(DependencyError):
    """Raised when more than one step uses the same ID."""

    pass


def _duplicate_ids(step_ids: list[str]) -> list[str]:
    """Return the IDs used by more than one step, in order of first appearance."""
    seen: set[str] = set()
    duplicates: list[str] = []
    for step_id in step_ids:
        if step_id in seen and step_id not in duplicates:
            duplicates.append(step_id)
        seen.add(step_id)
    return duplicates


def validate_dependencies(workflow: WorkflowDefinition) -> list[str]:
    """
    Validate workflow dependencies.

    Checks for:
    - Step IDs used by more than one step
    - Missing dependencies (referencing non-existent steps)
    - Self-dependencies
    - Cyclic dependencies

    Args:
        workflow: Workflow definition to validate

    Returns:
        List of error messages (empty if valid). Problems are reported here, not raised.
    """
    errors = []
    for step_id in _duplicate_ids(workflow.get_step_ids()):
        errors.append(f"Step ID '{step_id}' is used by more than one step")
    step_ids = set(workflow.get_step_ids())

    for step in workflow.steps:
        # Check for self-dependency
        if step.id in step.depends_on:
            errors.append(f"Step '{step.id}' depends on itself")

        # Check for missing dependencies
        for dep_id in step.depends_on:
            if dep_id not in step_ids:
                errors.append(f"Step '{step.id}' depends on non-existent step '{dep_id}'")

    # Check for cycles (duplicate IDs and missing dependencies are already reported above)
    try:
        resolve_execution_order(workflow)
    except CyclicDependencyError as e:
        errors.append(str(e))
    except (DuplicateStepError, MissingDependencyError):
        # The specific IDs and dependencies were already reported above.
        pass

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
        DuplicateStepError: If more than one step uses the same ID
    """
    step_ids = workflow.get_step_ids()
    duplicates = _duplicate_ids(step_ids)
    if duplicates:
        raise DuplicateStepError(f"Step IDs used by more than one step: {duplicates}")
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

    def get_config_flag(*keys: str, default: bool = False) -> bool:
        for key in keys:
            if key in config:
                return bool(config[key])
        return default

    # Simple evaluation - for now just handle common patterns
    # TODO: Implement proper expression evaluation

    # Check for "not config.without_html" pattern
    if condition.strip() == "${not config.without_html}":
        return not get_config_flag("without_html", "without-html", default=False)

    # Check for "${config.key}" / "${config.step.key}" pattern (dotted path into nested dicts)
    if condition.startswith("${config.") and condition.endswith("}"):
        path = condition[9:-1]  # Extract key path from ${config.key.subkey}
        value: Any = config
        for key in path.split("."):
            if not isinstance(value, dict) or key not in value:
                return False
            value = value[key]
        return bool(value)

    # Default to true for unrecognized conditions
    return True
