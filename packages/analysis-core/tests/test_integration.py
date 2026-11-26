"""Integration tests for analysis-core pipeline."""

import json

from analysis_core import PipelineOrchestrator
from analysis_core.orchestrator import PipelineResult


class TestPipelineIntegration:
    """Integration tests for the pipeline."""

    def test_full_plan_execution(self, tmp_path):
        """Test that all default steps are planned for execution."""
        # Create config file
        config_path = tmp_path / "test.json"
        config_path.write_text(
            json.dumps(
                {
                    "input": "test",
                    "question": "Test question?",
                    "provider": "local",
                }
            )
        )

        input_dir = tmp_path / "inputs"
        output_dir = tmp_path / "outputs"
        input_dir.mkdir()

        orchestrator = PipelineOrchestrator.from_config(
            config_path=config_path,
            skip_interaction=True,
            output_base_dir=output_dir,
            input_base_dir=input_dir,
        )

        plan = orchestrator.get_plan()

        # All 11 default steps should be in the plan
        assert len(plan) == 11

        step_names = [p["step"] for p in plan]
        expected_steps = [
            "extraction",
            "opinion_classification",
            "opinion_stance",
            "embedding",
            "opinion_novelty",
            "hierarchical_clustering",
            "hierarchical_initial_labelling",
            "hierarchical_merge_labelling",
            "hierarchical_overview",
            "hierarchical_aggregation",
            "hierarchical_visualization",
        ]
        assert step_names == expected_steps

    def test_run_default_uses_workflow_path(self, tmp_path, monkeypatch):
        """Test the default execution path delegates to run_workflow."""
        config = {
            "input": "test",
            "question": "Test?",
            "output_dir": "test",
            "plan": [{"step": "extraction", "run": True}],
        }

        orchestrator = PipelineOrchestrator(
            config=config,
            output_base_dir=tmp_path,
        )

        expected = PipelineResult(success=True, total_token_usage=42)
        monkeypatch.setattr(orchestrator, "run_workflow", lambda: expected)

        result = orchestrator.run_default()

        assert result is expected

    def test_run_workflow_reports_legacy_step_names(self, tmp_path, monkeypatch):
        """Test workflow execution returns legacy step names in PipelineResult."""
        from analysis_core.plugin import StepOutputs
        from analysis_core.workflow.definition import StepResult as WorkflowStepResult
        from analysis_core.workflow.definition import WorkflowResult

        orchestrator = PipelineOrchestrator.from_dict(
            config={
                "name": "demo",
                "input": "demo",
                "question": "Test?",
                "provider": "local",
                "model": "dummy",
            },
            output_dir="demo",
            output_base_dir=tmp_path / "outputs",
            input_base_dir=tmp_path / "inputs",
        )

        class FakeEngine:
            def run(self, workflow, config, ctx, on_step_start=None, on_step_complete=None, skip_steps=None):
                result = WorkflowResult(workflow_id="test")
                step_result = WorkflowStepResult(
                    step_id="visualization",
                    success=True,
                    outputs=StepOutputs(artifacts={"html": ctx.output_dir / "report.html"}),
                )
                if on_step_start:
                    on_step_start("visualization")
                if on_step_complete:
                    on_step_complete("visualization", step_result)
                result.step_results["visualization"] = step_result
                return result

        monkeypatch.setattr("analysis_core.workflow.WorkflowEngine", FakeEngine)

        result = orchestrator.run_workflow()

        assert result.success is True
        assert [step.step_name for step in result.steps] == ["hierarchical_visualization"]

    def test_run_workflow_records_step_durations(self, tmp_path, monkeypatch):
        """workflow 経由（CLI の既定）でも、段ごとの所要時間を status と PipelineResult に記録する（#1195）"""
        import time

        from analysis_core.plugin import StepOutputs
        from analysis_core.workflow.definition import StepResult as WorkflowStepResult
        from analysis_core.workflow.definition import WorkflowResult

        orchestrator = PipelineOrchestrator.from_dict(
            config={"name": "demo", "input": "demo", "question": "Test?", "provider": "local", "model": "dummy"},
            output_dir="demo",
            output_base_dir=tmp_path / "outputs",
            input_base_dir=tmp_path / "inputs",
        )

        class FakeEngine:
            def run(self, workflow, config, ctx, on_step_start=None, on_step_complete=None, skip_steps=None):
                result = WorkflowResult(workflow_id="test")
                step_result = WorkflowStepResult(
                    step_id="visualization",
                    success=True,
                    outputs=StepOutputs(artifacts={"html": ctx.output_dir / "report.html"}),
                )
                on_step_start("visualization")
                time.sleep(0.05)
                on_step_complete("visualization", step_result)
                result.step_results["visualization"] = step_result
                return result

        monkeypatch.setattr("analysis_core.workflow.WorkflowEngine", FakeEngine)

        result = orchestrator.run_workflow()

        assert result.steps[0].duration_seconds >= 0.05
        status = json.loads((tmp_path / "outputs" / "demo" / "hierarchical_status.json").read_text())
        job = next(j for j in status["completed_jobs"] if j["step"] == "hierarchical_visualization")
        assert job["duration"] >= 0.05
