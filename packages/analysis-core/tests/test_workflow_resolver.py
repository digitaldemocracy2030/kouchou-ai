"""Tests for workflow dependency validation and ordering (workflow/resolver.py)."""

import pytest

from analysis_core.workflow import (
    CyclicDependencyError,
    DuplicateStepError,
    MissingDependencyError,
    WorkflowDefinition,
    WorkflowEngine,
    WorkflowExecutionError,
    WorkflowStep,
    resolve_execution_order,
    validate_dependencies,
)


def _workflow(*steps: tuple[str, list[str]]) -> WorkflowDefinition:
    return WorkflowDefinition(
        id="test",
        version="1",
        steps=[WorkflowStep(id=step_id, plugin="p", depends_on=deps) for step_id, deps in steps],
    )


class TestResolveExecutionOrder:
    def test_dependencies_come_first(self):
        order = resolve_execution_order(_workflow(("c", ["a", "b"]), ("b", ["a"]), ("a", [])))
        assert order == ["a", "b", "c"]

    def test_repeated_dependency_is_counted_once_per_occurrence(self):
        order = resolve_execution_order(_workflow(("a", []), ("b", ["a", "a"])))
        assert order == ["a", "b"]

    def test_cycle(self):
        with pytest.raises(CyclicDependencyError, match=r"\['a', 'b'\]"):
            resolve_execution_order(_workflow(("a", ["b"]), ("b", ["a"]), ("c", [])))

    def test_missing_dependency(self):
        with pytest.raises(MissingDependencyError, match="non-existent step 'x'"):
            resolve_execution_order(_workflow(("a", ["x"])))

    def test_duplicate_id_is_not_reported_as_a_cycle(self):
        with pytest.raises(DuplicateStepError, match=r"\['a'\]"):
            resolve_execution_order(_workflow(("a", []), ("a", [])))


class TestValidateDependencies:
    def test_valid(self):
        assert validate_dependencies(_workflow(("a", []), ("b", ["a"]))) == []

    def test_missing_dependency_is_listed_not_raised(self):
        errors = validate_dependencies(_workflow(("a", ["x"]), ("b", ["a"])))
        assert errors == ["Step 'a' depends on non-existent step 'x'"]

    def test_missing_and_self_dependency_are_both_listed(self):
        errors = validate_dependencies(_workflow(("a", ["a", "x"])))
        assert errors == ["Step 'a' depends on itself", "Step 'a' depends on non-existent step 'x'"]

    def test_self_dependency_is_also_a_cycle(self):
        errors = validate_dependencies(_workflow(("a", ["a"])))
        assert errors[0] == "Step 'a' depends on itself"
        assert "Cyclic dependency" in errors[1]

    def test_duplicate_id(self):
        errors = validate_dependencies(_workflow(("a", []), ("a", []), ("b", ["a"])))
        assert errors == ["Step ID 'a' is used by more than one step"]


class TestEngineRejectsInvalidWorkflow:
    @pytest.mark.parametrize(
        "workflow",
        [
            _workflow(("a", ["x"])),
            _workflow(("a", []), ("a", [])),
            _workflow(("a", ["b"]), ("b", ["a"])),
        ],
    )
    def test_invalid_workflow_raises_workflow_execution_error(self, workflow, tmp_path):
        from analysis_core.plugin import StepContext

        ctx = StepContext(output_dir=tmp_path, input_dir=tmp_path, dataset="d", provider="local", model="m")
        with pytest.raises(WorkflowExecutionError, match="Invalid workflow"):
            WorkflowEngine().run(workflow, {}, ctx)
