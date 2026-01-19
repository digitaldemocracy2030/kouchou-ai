"""Tests for WorkflowEngine."""

from pathlib import Path
from typing import Any

import pytest

from analysis_core.plugin import (
    AnalysisStepPlugin,
    PluginMetadata,
    PluginRegistry,
    StepContext,
    StepInputs,
    StepOutputs,
    step_plugin,
)
from analysis_core.workflow import (
    WorkflowDefinition,
    WorkflowEngine,
    WorkflowStep,
)
from analysis_core.workflow.engine import WorkflowExecutionError


@pytest.fixture
def test_ctx(tmp_path):
    """Create a test StepContext."""
    output_dir = tmp_path / "output"
    input_dir = tmp_path / "input"
    output_dir.mkdir()
    input_dir.mkdir()

    return StepContext(
        output_dir=output_dir,
        input_dir=input_dir,
        dataset="test",
        provider="openai",
        model="gpt-4o-mini",
    )


@pytest.fixture
def test_registry():
    """Create a fresh plugin registry for testing."""
    return PluginRegistry()


class TestWorkflowEngineValidation:
    """Tests for workflow engine input/config validation."""

    def test_validates_missing_inputs(self, test_ctx, test_registry):
        """Test that missing required inputs cause validation failure."""
        # Create a plugin that requires an input
        @step_plugin(
            id="test.requires_input",
            version="1.0.0",
            inputs=["required_data"],
            outputs=["result"],
        )
        def requires_input_plugin(
            ctx: StepContext, inputs: StepInputs, config: dict
        ) -> StepOutputs:
            # This should not be called if validation fails
            return StepOutputs(artifacts={"result": ctx.output_dir / "result.txt"})

        test_registry.register(requires_input_plugin)

        # Create workflow with the plugin
        workflow = WorkflowDefinition(
            id="test-workflow",
            version="1.0.0",
            steps=[
                WorkflowStep(
                    id="step1",
                    plugin="test.requires_input",
                ),
            ],
        )

        engine = WorkflowEngine(registry=test_registry)

        # Run workflow - should fail validation because required_data is missing
        result = engine.run(workflow, {}, test_ctx)

        assert not result.success
        assert "step1" in result.step_results
        assert not result.step_results["step1"].success
        assert "Missing required input: required_data" in result.step_results["step1"].error

    def test_validates_config(self, test_ctx, test_registry):
        """Test that config validation is called."""

        # Create a plugin with custom config validation
        class ConfigValidatingPlugin(AnalysisStepPlugin):
            @property
            def metadata(self) -> PluginMetadata:
                return PluginMetadata(
                    id="test.config_validator",
                    version="1.0.0",
                    inputs=[],
                    outputs=["result"],
                )

            def run(
                self, ctx: StepContext, inputs: StepInputs, config: dict
            ) -> StepOutputs:
                return StepOutputs(artifacts={"result": ctx.output_dir / "result.txt"})

            def validate_config(self, config: dict) -> list[str]:
                errors = []
                if "required_option" not in config:
                    errors.append("Missing required_option in config")
                return errors

        test_registry.register(ConfigValidatingPlugin())

        workflow = WorkflowDefinition(
            id="test-workflow",
            version="1.0.0",
            steps=[
                WorkflowStep(
                    id="step1",
                    plugin="test.config_validator",
                ),
            ],
        )

        engine = WorkflowEngine(registry=test_registry)

        # Run workflow - should fail because config is missing required_option
        result = engine.run(workflow, {}, test_ctx)

        assert not result.success
        assert "step1" in result.step_results
        assert not result.step_results["step1"].success
        assert "Missing required_option" in result.step_results["step1"].error

    def test_optional_step_validation_failure_continues(self, test_ctx, test_registry):
        """Test that optional step validation failure allows workflow to continue."""
        @step_plugin(
            id="test.optional_step",
            version="1.0.0",
            inputs=["missing_input"],
            outputs=["optional_result"],
        )
        def optional_step_plugin(
            ctx: StepContext, inputs: StepInputs, config: dict
        ) -> StepOutputs:
            return StepOutputs(artifacts={"optional_result": ctx.output_dir / "opt.txt"})

        @step_plugin(
            id="test.final_step",
            version="1.0.0",
            inputs=[],
            outputs=["final_result"],
        )
        def final_step_plugin(
            ctx: StepContext, inputs: StepInputs, config: dict
        ) -> StepOutputs:
            (ctx.output_dir / "final.txt").write_text("done")
            return StepOutputs(artifacts={"final_result": ctx.output_dir / "final.txt"})

        test_registry.register(optional_step_plugin)
        test_registry.register(final_step_plugin)

        workflow = WorkflowDefinition(
            id="test-workflow",
            version="1.0.0",
            steps=[
                WorkflowStep(
                    id="optional",
                    plugin="test.optional_step",
                    optional=True,
                ),
                WorkflowStep(
                    id="final",
                    plugin="test.final_step",
                    depends_on=["optional"],
                ),
            ],
        )

        engine = WorkflowEngine(registry=test_registry)
        result = engine.run(workflow, {}, test_ctx)

        # Workflow should succeed because optional step is skipped
        assert result.success
        assert result.step_results["optional"].skipped
        assert not result.step_results["optional"].success
        assert "Missing required input" in result.step_results["optional"].error
        assert result.step_results["final"].success

    def test_valid_inputs_passes_validation(self, test_ctx, test_registry):
        """Test that valid inputs allow step to run."""
        @step_plugin(
            id="test.producer",
            version="1.0.0",
            inputs=[],
            outputs=["data"],
        )
        def producer_plugin(
            ctx: StepContext, inputs: StepInputs, config: dict
        ) -> StepOutputs:
            data_file = ctx.output_dir / "data.txt"
            data_file.write_text("produced data")
            return StepOutputs(artifacts={"data": data_file})

        @step_plugin(
            id="test.consumer",
            version="1.0.0",
            inputs=["data"],
            outputs=["result"],
        )
        def consumer_plugin(
            ctx: StepContext, inputs: StepInputs, config: dict
        ) -> StepOutputs:
            # Should receive the data artifact
            assert "data" in inputs.artifacts
            result_file = ctx.output_dir / "result.txt"
            result_file.write_text("consumed")
            return StepOutputs(artifacts={"result": result_file})

        test_registry.register(producer_plugin)
        test_registry.register(consumer_plugin)

        workflow = WorkflowDefinition(
            id="test-workflow",
            version="1.0.0",
            steps=[
                WorkflowStep(
                    id="produce",
                    plugin="test.producer",
                ),
                WorkflowStep(
                    id="consume",
                    plugin="test.consumer",
                    depends_on=["produce"],
                ),
            ],
        )

        engine = WorkflowEngine(registry=test_registry)
        result = engine.run(workflow, {}, test_ctx)

        assert result.success
        assert result.step_results["produce"].success
        assert result.step_results["consume"].success

    def test_validation_stops_workflow_early(self, test_ctx, test_registry):
        """Test that validation failure stops workflow before downstream steps."""
        call_count = {"downstream": 0}

        @step_plugin(
            id="test.failing_step",
            version="1.0.0",
            inputs=["nonexistent"],
            outputs=["data"],
        )
        def failing_step_plugin(
            ctx: StepContext, inputs: StepInputs, config: dict
        ) -> StepOutputs:
            return StepOutputs(artifacts={"data": ctx.output_dir / "data.txt"})

        @step_plugin(
            id="test.downstream_step",
            version="1.0.0",
            inputs=["data"],
            outputs=["result"],
        )
        def downstream_step_plugin(
            ctx: StepContext, inputs: StepInputs, config: dict
        ) -> StepOutputs:
            call_count["downstream"] += 1
            return StepOutputs(artifacts={"result": ctx.output_dir / "result.txt"})

        test_registry.register(failing_step_plugin)
        test_registry.register(downstream_step_plugin)

        workflow = WorkflowDefinition(
            id="test-workflow",
            version="1.0.0",
            steps=[
                WorkflowStep(
                    id="fail",
                    plugin="test.failing_step",
                ),
                WorkflowStep(
                    id="downstream",
                    plugin="test.downstream_step",
                    depends_on=["fail"],
                ),
            ],
        )

        engine = WorkflowEngine(registry=test_registry)
        result = engine.run(workflow, {}, test_ctx)

        assert not result.success
        assert "fail" in result.step_results
        assert not result.step_results["fail"].success
        # Downstream should not be in results because workflow stopped
        assert "downstream" not in result.step_results
        # Downstream should not have been called
        assert call_count["downstream"] == 0
