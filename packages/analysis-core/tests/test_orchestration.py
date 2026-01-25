"""Tests for orchestration module."""

import json
from pathlib import Path

import pytest


class TestInitialization:
    """Test initialization function."""

    def test_initialization_creates_output_dir(self, tmp_path):
        """Test that initialization creates output directory."""
        from analysis_core.core import initialization

        # Create a minimal config file
        config_path = tmp_path / "test_job.json"
        config_path.write_text(
            json.dumps(
                {
                    "input": "test_input",
                    "question": "What are the main themes?",
                    "provider": "openai",
                }
            )
        )

        # Create input and output directories
        input_dir = tmp_path / "inputs"
        output_dir = tmp_path / "outputs"
        input_dir.mkdir()

        # Run initialization
        config = initialization(
            config_path=config_path,
            skip_interaction=True,
            output_base_dir=output_dir,
            input_base_dir=input_dir,
        )

        # Check output directory was created
        assert (output_dir / "test_job").exists()

        # Check config was populated
        assert config["output_dir"] == "test_job"
        assert config["input"] == "test_input"
        assert config["question"] == "What are the main themes?"
        assert config["model"] == "gpt-4o-mini"  # default
        assert "plan" in config

    def test_initialization_loads_specs(self, tmp_path):
        """Test that initialization loads step specs."""
        from analysis_core.core import get_specs, initialization

        # Create config file
        config_path = tmp_path / "job.json"
        config_path.write_text(
            json.dumps(
                {
                    "input": "test",
                    "question": "Test?",
                    "provider": "openai",
                }
            )
        )

        input_dir = tmp_path / "inputs"
        output_dir = tmp_path / "outputs"
        input_dir.mkdir()

        initialization(
            config_path=config_path,
            skip_interaction=True,
            output_base_dir=output_dir,
            input_base_dir=input_dir,
        )

        specs = get_specs()
        assert len(specs) == 8
        step_names = [s["step"] for s in specs]
        assert "extraction" in step_names
        assert "embedding" in step_names
        assert "hierarchical_clustering" in step_names

    def test_initialization_sets_default_options(self, tmp_path):
        """Test that initialization sets default options for steps."""
        from analysis_core.core import initialization

        config_path = tmp_path / "job.json"
        config_path.write_text(
            json.dumps(
                {
                    "input": "test",
                    "question": "Test?",
                    "provider": "openai",
                }
            )
        )

        input_dir = tmp_path / "inputs"
        output_dir = tmp_path / "outputs"
        input_dir.mkdir()

        config = initialization(
            config_path=config_path,
            skip_interaction=True,
            output_base_dir=output_dir,
            input_base_dir=input_dir,
        )

        # Check default options were set
        assert "extraction" in config
        assert config["extraction"]["limit"] == 1000
        assert config["extraction"]["workers"] == 1

        assert "hierarchical_clustering" in config
        assert config["hierarchical_clustering"]["cluster_nums"] == [3, 6]

    def test_initialization_force_flag(self, tmp_path):
        """Test that force flag is set in config."""
        from analysis_core.core import initialization

        config_path = tmp_path / "job.json"
        config_path.write_text(
            json.dumps(
                {
                    "input": "test",
                    "question": "Test?",
                    "provider": "openai",
                }
            )
        )

        input_dir = tmp_path / "inputs"
        output_dir = tmp_path / "outputs"
        input_dir.mkdir()

        config = initialization(
            config_path=config_path,
            force=True,
            skip_interaction=True,
            output_base_dir=output_dir,
            input_base_dir=input_dir,
        )

        assert config.get("force") is True

    def test_initialization_only_step(self, tmp_path):
        """Test that only step is set in config."""
        from analysis_core.core import initialization

        config_path = tmp_path / "job.json"
        config_path.write_text(
            json.dumps(
                {
                    "input": "test",
                    "question": "Test?",
                    "provider": "openai",
                }
            )
        )

        input_dir = tmp_path / "inputs"
        output_dir = tmp_path / "outputs"
        input_dir.mkdir()

        config = initialization(
            config_path=config_path,
            only="extraction",
            skip_interaction=True,
            output_base_dir=output_dir,
            input_base_dir=input_dir,
        )

        assert config.get("only") == "extraction"

    def test_initialization_without_html(self, tmp_path):
        """Test that without_html flag is set."""
        from analysis_core.core import initialization

        config_path = tmp_path / "job.json"
        config_path.write_text(
            json.dumps(
                {
                    "input": "test",
                    "question": "Test?",
                    "provider": "openai",
                }
            )
        )

        input_dir = tmp_path / "inputs"
        output_dir = tmp_path / "outputs"
        input_dir.mkdir()

        config = initialization(
            config_path=config_path,
            without_html=True,
            skip_interaction=True,
            output_base_dir=output_dir,
            input_base_dir=input_dir,
        )

        assert config.get("without-html") is True


class TestValidateConfig:
    """Test config validation."""

    def test_validate_config_missing_input(self):
        """Test validation fails for missing input."""
        from analysis_core.core import load_specs, validate_config
        from analysis_core.core.orchestration import _PACKAGE_DIR

        specs = load_specs(_PACKAGE_DIR / "specs" / "hierarchical_specs.json")

        with pytest.raises(Exception, match="Missing required field 'input'"):
            validate_config({"question": "Test?"}, specs)

    def test_validate_config_missing_question(self):
        """Test validation fails for missing question."""
        from analysis_core.core import load_specs, validate_config
        from analysis_core.core.orchestration import _PACKAGE_DIR

        specs = load_specs(_PACKAGE_DIR / "specs" / "hierarchical_specs.json")

        with pytest.raises(Exception, match="Missing required field 'question'"):
            validate_config({"input": "test"}, specs)

    def test_validate_config_valid(self):
        """Test validation passes for valid config."""
        from analysis_core.core import load_specs, validate_config
        from analysis_core.core.orchestration import _PACKAGE_DIR

        specs = load_specs(_PACKAGE_DIR / "specs" / "hierarchical_specs.json")

        # Should not raise
        validate_config(
            {
                "input": "test",
                "question": "Test?",
                "model": "gpt-4o-mini",
                "provider": "openai",
            },
            specs,
        )


class TestDecideWhatToRun:
    """Test decide_what_to_run function."""

    def test_decide_first_run(self, tmp_path):
        """Test plan for first run (no previous status)."""
        from analysis_core.core import decide_what_to_run, load_specs
        from analysis_core.core.orchestration import _PACKAGE_DIR

        specs = load_specs(_PACKAGE_DIR / "specs" / "hierarchical_specs.json")

        config = {
            "input": "test",
            "question": "Test?",
            "output_dir": "test",
        }

        plan = decide_what_to_run(config, None, specs, tmp_path)

        # All steps should run on first execution
        assert len(plan) == 8
        assert all(step["run"] for step in plan)

    def test_decide_skip_html(self, tmp_path):
        """Test that visualization step is skipped with without-html."""
        from analysis_core.core import decide_what_to_run, load_specs
        from analysis_core.core.orchestration import _PACKAGE_DIR

        specs = load_specs(_PACKAGE_DIR / "specs" / "hierarchical_specs.json")

        config = {
            "input": "test",
            "question": "Test?",
            "output_dir": "test",
            "without-html": True,
        }

        plan = decide_what_to_run(config, None, specs, tmp_path)

        # Visualization step should be skipped
        viz_step = next(s for s in plan if s["step"] == "hierarchical_visualization")
        assert viz_step["run"] is False
        assert "skipping html" in viz_step["reason"]


class TestPipelineOrchestrator:
    """Test PipelineOrchestrator class."""

    def test_orchestrator_init(self, tmp_path):
        """Test orchestrator initialization with config dict."""
        from analysis_core import PipelineOrchestrator

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

        assert orchestrator.config == config
        assert orchestrator.output_base_dir == tmp_path
        assert len(orchestrator.steps) == 8

    def test_orchestrator_from_config(self, tmp_path):
        """Test orchestrator creation from config file."""
        from analysis_core import PipelineOrchestrator

        # Create config file
        config_path = tmp_path / "job.json"
        config_path.write_text(
            json.dumps(
                {
                    "input": "test",
                    "question": "Test?",
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

        assert orchestrator.config["input"] == "test"
        assert orchestrator.config["question"] == "Test?"
        assert "plan" in orchestrator.config

    def test_orchestrator_register_step(self, tmp_path):
        """Test registering a custom step."""
        from analysis_core import PipelineOrchestrator

        config = {
            "input": "test",
            "question": "Test?",
            "output_dir": "test",
        }

        orchestrator = PipelineOrchestrator(config=config, output_base_dir=tmp_path)

        def custom_step(config):
            pass

        orchestrator.register_step("custom", custom_step)

        assert "custom" in orchestrator._step_functions
        assert orchestrator._step_functions["custom"] is custom_step

    def test_orchestrator_get_plan(self, tmp_path):
        """Test getting execution plan."""
        from analysis_core import PipelineOrchestrator

        plan = [
            {"step": "extraction", "run": True, "reason": "first run"},
            {"step": "embedding", "run": True, "reason": "first run"},
        ]

        config = {
            "input": "test",
            "question": "Test?",
            "output_dir": "test",
            "plan": plan,
        }

        orchestrator = PipelineOrchestrator(config=config, output_base_dir=tmp_path)

        assert orchestrator.get_plan() == plan

    def test_orchestrator_get_status(self, tmp_path):
        """Test getting status."""
        from analysis_core import PipelineOrchestrator

        config = {
            "input": "test",
            "question": "Test?",
            "output_dir": "test",
            "status": "running",
            "current_job": "extraction",
            "completed_jobs": [],
            "total_token_usage": 100,
            "plan": [],
        }

        orchestrator = PipelineOrchestrator(config=config, output_base_dir=tmp_path)
        status = orchestrator.get_status()

        assert status["status"] == "running"
        assert status["current_job"] == "extraction"
        assert status["total_token_usage"] == 100
