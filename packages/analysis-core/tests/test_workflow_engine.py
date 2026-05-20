"""Tests for WorkflowEngine."""

from pathlib import Path

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
        def requires_input_plugin(ctx: StepContext, inputs: StepInputs, config: dict) -> StepOutputs:
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

            def run(self, ctx: StepContext, inputs: StepInputs, config: dict) -> StepOutputs:
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
        def optional_step_plugin(ctx: StepContext, inputs: StepInputs, config: dict) -> StepOutputs:
            return StepOutputs(artifacts={"optional_result": ctx.output_dir / "opt.txt"})

        @step_plugin(
            id="test.final_step",
            version="1.0.0",
            inputs=[],
            outputs=["final_result"],
        )
        def final_step_plugin(ctx: StepContext, inputs: StepInputs, config: dict) -> StepOutputs:
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
        def producer_plugin(ctx: StepContext, inputs: StepInputs, config: dict) -> StepOutputs:
            data_file = ctx.output_dir / "data.txt"
            data_file.write_text("produced data")
            return StepOutputs(artifacts={"data": data_file})

        @step_plugin(
            id="test.consumer",
            version="1.0.0",
            inputs=["data"],
            outputs=["result"],
        )
        def consumer_plugin(ctx: StepContext, inputs: StepInputs, config: dict) -> StepOutputs:
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
        def failing_step_plugin(ctx: StepContext, inputs: StepInputs, config: dict) -> StepOutputs:
            return StepOutputs(artifacts={"data": ctx.output_dir / "data.txt"})

        @step_plugin(
            id="test.downstream_step",
            version="1.0.0",
            inputs=["data"],
            outputs=["result"],
        )
        def downstream_step_plugin(ctx: StepContext, inputs: StepInputs, config: dict) -> StepOutputs:
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

    def test_seeds_comments_artifact_from_input_config(self, test_ctx, test_registry):
        """Test that the engine exposes the input CSV as the initial comments artifact."""

        seen = {}

        @step_plugin(
            id="test.comments_consumer",
            version="1.0.0",
            inputs=["comments"],
            outputs=["result"],
        )
        def comments_consumer(ctx: StepContext, inputs: StepInputs, config: dict) -> StepOutputs:
            seen["comments"] = inputs.artifacts["comments"]
            return StepOutputs(artifacts={"result": ctx.output_dir / "result.txt"})

        test_registry.register(comments_consumer)

        workflow = WorkflowDefinition(
            id="test-workflow",
            version="1.0.0",
            steps=[WorkflowStep(id="consume", plugin="test.comments_consumer")],
        )

        engine = WorkflowEngine(registry=test_registry)
        result = engine.run(workflow, {"input": "survey-comments"}, test_ctx)

        assert result.success
        assert seen["comments"] == test_ctx.input_dir / "survey-comments.csv"

    def test_condition_accepts_legacy_without_html_key(self, test_ctx, test_registry):
        """Test that workflow conditions honor the legacy without-html config key."""

        @step_plugin(
            id="test.optional_html",
            version="1.0.0",
            inputs=[],
            outputs=["html"],
        )
        def optional_html(ctx: StepContext, inputs: StepInputs, config: dict) -> StepOutputs:
            return StepOutputs(artifacts={"html": ctx.output_dir / "report.html"})

        test_registry.register(optional_html)

        workflow = WorkflowDefinition(
            id="test-workflow",
            version="1.0.0",
            steps=[
                WorkflowStep(
                    id="html",
                    plugin="test.optional_html",
                    condition="${not config.without_html}",
                )
            ],
        )

        engine = WorkflowEngine(registry=test_registry)
        result = engine.run(workflow, {"without-html": True}, test_ctx)

        assert result.success
        assert result.step_results["html"].skipped

    def test_seeds_existing_output_artifacts(self, test_ctx, test_registry):
        """Test that existing output files can satisfy plugin input requirements."""

        existing_args = test_ctx.output_dir / "args.csv"
        existing_args.write_text("arg-id,argument\nA1,test\n", encoding="utf-8")
        seen = {}

        @step_plugin(
            id="test.arguments_consumer",
            version="1.0.0",
            inputs=["arguments"],
            outputs=["result"],
        )
        def arguments_consumer(ctx: StepContext, inputs: StepInputs, config: dict) -> StepOutputs:
            seen["arguments"] = inputs.artifacts["arguments"]
            return StepOutputs(artifacts={"result": ctx.output_dir / "result.txt"})

        test_registry.register(arguments_consumer)

        workflow = WorkflowDefinition(
            id="test-workflow",
            version="1.0.0",
            steps=[WorkflowStep(id="consume", plugin="test.arguments_consumer")],
        )

        engine = WorkflowEngine(registry=test_registry)
        result = engine.run(workflow, {}, test_ctx)

        assert result.success
        assert seen["arguments"] == existing_args

    def test_skip_steps_marks_step_skipped(self, test_ctx, test_registry):
        """Test explicit skip_steps support for rerun planning."""

        calls = {"producer": 0, "consumer": 0}
        existing_args = test_ctx.output_dir / "args.csv"
        existing_args.write_text("arg-id,argument\nA1,old\n", encoding="utf-8")

        @step_plugin(
            id="test.producer",
            version="1.0.0",
            inputs=[],
            outputs=["arguments"],
        )
        def producer_plugin(ctx: StepContext, inputs: StepInputs, config: dict) -> StepOutputs:
            calls["producer"] += 1
            return StepOutputs(artifacts={"arguments": ctx.output_dir / "args.csv"})

        @step_plugin(
            id="test.consumer",
            version="1.0.0",
            inputs=["arguments"],
            outputs=["result"],
        )
        def consumer_plugin(ctx: StepContext, inputs: StepInputs, config: dict) -> StepOutputs:
            calls["consumer"] += 1
            assert inputs.artifacts["arguments"] == existing_args
            return StepOutputs(artifacts={"result": ctx.output_dir / "result.txt"})

        test_registry.register(producer_plugin)
        test_registry.register(consumer_plugin)

        workflow = WorkflowDefinition(
            id="test-workflow",
            version="1.0.0",
            steps=[
                WorkflowStep(id="produce", plugin="test.producer"),
                WorkflowStep(id="consume", plugin="test.consumer", depends_on=["produce"]),
            ],
        )

        engine = WorkflowEngine(registry=test_registry)
        result = engine.run(workflow, {}, test_ctx, skip_steps={"produce"})

        assert result.success
        assert result.step_results["produce"].skipped is True
        assert calls["producer"] == 0
        assert calls["consumer"] == 1


class TestWorkflowEngineOutputDir:
    """Tests for workflow engine output directory handling."""

    def test_plugin_uses_ctx_output_dir_not_hardcoded_path(self, test_registry):
        """Verify plugins use ctx.output_dir, not hardcoded Path('outputs').

        This is a regression test for the bug where builtin plugins used
        Path("outputs") / ctx.dataset instead of ctx.output_dir.
        """
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            # Use a custom output path that is NOT "outputs"
            custom_output = Path(tmpdir) / "custom_output_location" / "my_dataset"
            custom_output.mkdir(parents=True)
            input_dir = Path(tmpdir) / "input"
            input_dir.mkdir()

            ctx = StepContext(
                output_dir=custom_output,
                input_dir=input_dir,
                dataset="my_dataset",
                provider="openai",
                model="gpt-4o-mini",
            )

            # Create a plugin that writes to ctx.output_dir
            @step_plugin(
                id="test.output_dir_check",
                version="1.0.0",
                inputs=[],
                outputs=["artifact"],
            )
            def output_dir_plugin(ctx: StepContext, inputs: StepInputs, config: dict) -> StepOutputs:
                # Write to ctx.output_dir (correct behavior)
                artifact_path = ctx.output_dir / "test_artifact.txt"
                artifact_path.write_text("test content")
                return StepOutputs(artifacts={"artifact": artifact_path})

            test_registry.register(output_dir_plugin)

            workflow = WorkflowDefinition(
                id="test-workflow",
                version="1.0.0",
                steps=[
                    WorkflowStep(
                        id="output_check",
                        plugin="test.output_dir_check",
                    ),
                ],
            )

            engine = WorkflowEngine(registry=test_registry)
            result = engine.run(workflow, {}, ctx)

            # Verify workflow succeeded
            assert result.success
            assert result.step_results["output_check"].success

            # Verify artifact was created in custom_output, not in "outputs"
            artifact_path = result.step_results["output_check"].outputs.artifacts["artifact"]
            assert artifact_path.exists()
            assert str(custom_output) in str(artifact_path)
            assert "outputs" not in str(artifact_path).replace(str(tmpdir), "")

            # Verify the hardcoded path was NOT used
            hardcoded_path = Path("outputs") / "my_dataset" / "test_artifact.txt"
            assert not hardcoded_path.exists()

    def test_multiple_steps_share_output_dir(self, test_registry):
        """Verify multiple steps write to the same ctx.output_dir."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir) / "shared_output"
            output_dir.mkdir(parents=True)
            input_dir = Path(tmpdir) / "input"
            input_dir.mkdir()

            ctx = StepContext(
                output_dir=output_dir,
                input_dir=input_dir,
                dataset="test",
                provider="openai",
                model="gpt-4o-mini",
            )

            @step_plugin(
                id="test.step1",
                version="1.0.0",
                inputs=[],
                outputs=["file1"],
            )
            def step1_plugin(ctx: StepContext, inputs: StepInputs, config: dict) -> StepOutputs:
                path = ctx.output_dir / "file1.txt"
                path.write_text("step1")
                return StepOutputs(artifacts={"file1": path})

            @step_plugin(
                id="test.step2",
                version="1.0.0",
                inputs=["file1"],
                outputs=["file2"],
            )
            def step2_plugin(ctx: StepContext, inputs: StepInputs, config: dict) -> StepOutputs:
                path = ctx.output_dir / "file2.txt"
                path.write_text("step2")
                return StepOutputs(artifacts={"file2": path})

            test_registry.register(step1_plugin)
            test_registry.register(step2_plugin)

            workflow = WorkflowDefinition(
                id="test-workflow",
                version="1.0.0",
                steps=[
                    WorkflowStep(id="s1", plugin="test.step1"),
                    WorkflowStep(id="s2", plugin="test.step2", depends_on=["s1"]),
                ],
            )

            engine = WorkflowEngine(registry=test_registry)
            result = engine.run(workflow, {}, ctx)

            assert result.success

            # Both files should be in the same output_dir
            assert (output_dir / "file1.txt").exists()
            assert (output_dir / "file2.txt").exists()
            assert (output_dir / "file1.txt").read_text() == "step1"
            assert (output_dir / "file2.txt").read_text() == "step2"
