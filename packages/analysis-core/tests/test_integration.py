"""Integration tests for analysis-core pipeline."""

import json
from unittest.mock import MagicMock, patch

import pytest

from analysis_core import PipelineOrchestrator
from analysis_core.orchestrator import PipelineResult


class TestPipelineIntegration:
    """Integration tests for the pipeline."""

    def test_run_with_mocked_steps(self, tmp_path):
        """Test that pipeline run executes mocked steps in order."""
        # Create config
        config = {
            "input": "test",
            "question": "Test question?",
            "output_dir": "test",
            "provider": "openai",
            "plan": [
                {"step": "extraction", "run": True, "reason": "test"},
                {"step": "embedding", "run": True, "reason": "test"},
            ],
        }

        # Track step execution order
        executed_steps = []

        def mock_step(name):
            def _step(config):
                executed_steps.append(name)

            return _step

        # Create orchestrator with limited steps
        orchestrator = PipelineOrchestrator(
            config=config,
            output_base_dir=tmp_path,
            steps=["extraction", "embedding"],
        )

        # Register mocked step functions
        orchestrator.register_step("extraction", mock_step("extraction"))
        orchestrator.register_step("embedding", mock_step("embedding"))

        # Mock run_step to just call the step function
        with patch("analysis_core.orchestrator.run_step") as mock_run_step:

            def side_effect(step, func, config, output_base_dir):
                func(config)

            mock_run_step.side_effect = side_effect

            with patch("analysis_core.orchestrator.termination"):
                result = orchestrator.run()

        # Verify steps were executed in order
        assert executed_steps == ["extraction", "embedding"]
        assert isinstance(result, PipelineResult)

    def test_run_handles_step_failure(self, tmp_path):
        """Test that pipeline handles step failures gracefully."""
        config = {
            "input": "test",
            "question": "Test?",
            "output_dir": "test",
            "plan": [{"step": "extraction", "run": True}],
        }

        orchestrator = PipelineOrchestrator(
            config=config,
            output_base_dir=tmp_path,
            steps=["extraction"],
        )

        # Register a failing step
        def failing_step(config):
            raise RuntimeError("Step failed")

        orchestrator.register_step("extraction", failing_step)

        # Mock run_step to call the step function directly
        with patch("analysis_core.orchestrator.run_step") as mock_run_step:

            def side_effect(step, func, config, output_base_dir):
                func(config)

            mock_run_step.side_effect = side_effect

            with patch("analysis_core.orchestrator.termination"):
                result = orchestrator.run()

        # Verify failure was captured
        assert result.success is False
        assert "Step failed" in result.error
        assert len(result.steps) == 1
        assert result.steps[0].success is False

    def test_full_plan_execution(self, tmp_path):
        """Test that all 8 steps are planned for execution."""
        # Create config file
        config_path = tmp_path / "test.json"
        config_path.write_text(
            json.dumps(
                {
                    "input": "test",
                    "question": "Test question?",
                    "provider": "openai",
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

        # All 8 steps should be in the plan
        assert len(plan) == 8

        step_names = [p["step"] for p in plan]
        expected_steps = [
            "extraction",
            "embedding",
            "hierarchical_clustering",
            "hierarchical_initial_labelling",
            "hierarchical_merge_labelling",
            "hierarchical_overview",
            "hierarchical_aggregation",
            "hierarchical_visualization",
        ]
        assert step_names == expected_steps

    def test_status_tracking(self, tmp_path):
        """Test that status is properly tracked during execution."""
        config = {
            "input": "test",
            "question": "Test?",
            "output_dir": "test",
            "plan": [{"step": "extraction", "run": True}],
            "status": "pending",
        }

        orchestrator = PipelineOrchestrator(
            config=config,
            output_base_dir=tmp_path,
            steps=["extraction"],
        )

        # Register a step that updates status
        def step_with_status(cfg):
            cfg["status"] = "running"
            cfg["current_job"] = "extraction"

        orchestrator.register_step("extraction", step_with_status)

        with patch("analysis_core.orchestrator.run_step") as mock_run_step:

            def side_effect(step, func, config, output_base_dir):
                func(config)

            mock_run_step.side_effect = side_effect

            with patch("analysis_core.orchestrator.termination"):
                orchestrator.run()

        status = orchestrator.get_status()
        assert status["current_job"] == "extraction"
