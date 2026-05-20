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
                    "provider": "local",
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
                    "provider": "local",
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
                    "provider": "local",
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
        assert config["hierarchical_clustering"]["cluster_nums"] is None

    def test_initialization_force_flag(self, tmp_path):
        """Test that force flag is set in config."""
        from analysis_core.core import initialization

        config_path = tmp_path / "job.json"
        config_path.write_text(
            json.dumps(
                {
                    "input": "test",
                    "question": "Test?",
                    "provider": "local",
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
                    "provider": "local",
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
                    "provider": "local",
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

    def test_initialization_prefers_legacy_without_html_key(self, tmp_path):
        """Test conflicting without_html flags are reconciled to the legacy key."""
        from analysis_core.core import initialization

        config_path = tmp_path / "job.json"
        config_path.write_text(
            json.dumps(
                {
                    "input": "test",
                    "question": "Test?",
                    "provider": "local",
                    "without_html": False,
                    "without-html": True,
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

        assert config["without-html"] is True
        assert config["without_html"] is True


class TestValidateApiKeys:
    """Test API key validation."""

    def test_validate_api_keys_openai_missing(self, monkeypatch):
        """Test validation fails for missing OpenAI API key."""
        from analysis_core.core.orchestration import validate_api_keys

        # Set to empty string to prevent load_dotenv from loading it
        monkeypatch.setenv("OPENAI_API_KEY", "")

        with pytest.raises(RuntimeError, match="OPENAI_API_KEY environment variable is not set"):
            validate_api_keys("openai")

    def test_validate_api_keys_openai_with_env(self, monkeypatch):
        """Test validation passes when OpenAI API key is set."""
        from analysis_core.core.orchestration import validate_api_keys

        monkeypatch.setenv("OPENAI_API_KEY", "test-key")

        validate_api_keys("openai")

    def test_validate_api_keys_openai_with_user_key(self, monkeypatch):
        """Test validation passes with user-provided API key."""
        from analysis_core.core.orchestration import validate_api_keys

        # Set to empty string to prevent load_dotenv from loading it
        monkeypatch.setenv("OPENAI_API_KEY", "")

        validate_api_keys("openai", user_api_key="user-provided-key")

    def test_validate_api_keys_gemini_missing(self, monkeypatch):
        """Test validation fails for missing Gemini API key."""
        from analysis_core.core.orchestration import validate_api_keys

        # Set to empty string to prevent load_dotenv from loading it
        monkeypatch.setenv("GEMINI_API_KEY", "")

        with pytest.raises(RuntimeError, match="GEMINI_API_KEY environment variable is not set"):
            validate_api_keys("gemini")

    def test_validate_api_keys_azure_missing(self, monkeypatch):
        """Test validation fails for missing Azure environment variables."""
        from analysis_core.core.orchestration import validate_api_keys

        # Set to empty strings instead of deleting to prevent load_dotenv from loading them
        monkeypatch.setenv("AZURE_CHATCOMPLETION_ENDPOINT", "")
        monkeypatch.setenv("AZURE_CHATCOMPLETION_DEPLOYMENT_NAME", "")
        monkeypatch.setenv("AZURE_CHATCOMPLETION_API_KEY", "")
        monkeypatch.setenv("AZURE_CHATCOMPLETION_VERSION", "")

        with pytest.raises(RuntimeError, match="Azure OpenAI environment variables not set"):
            validate_api_keys("azure")

    def test_validate_api_keys_openrouter_missing(self, monkeypatch):
        """Test validation fails for missing OpenRouter API key."""
        from analysis_core.core.orchestration import validate_api_keys

        # Set to empty string to prevent load_dotenv from loading it
        monkeypatch.setenv("OPENROUTER_API_KEY", "")

        with pytest.raises(RuntimeError, match="OPENROUTER_API_KEY environment variable is not set"):
            validate_api_keys("openrouter")

    def test_validate_api_keys_local_no_key_needed(self):
        """Test validation passes for local provider without any keys."""
        from analysis_core.core.orchestration import validate_api_keys

        validate_api_keys("local")

    def test_validate_api_keys_unknown_provider(self):
        """Test validation fails for unknown provider."""
        from analysis_core.core.orchestration import validate_api_keys

        with pytest.raises(RuntimeError, match="Unknown provider"):
            validate_api_keys("unknown_provider")


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

    def test_from_dict_uses_previous_status_for_plan(self, tmp_path):
        """Test from_dict loads previous status and computes rerun plan."""
        from analysis_core import PipelineOrchestrator

        output_dir = tmp_path / "outputs" / "demo"
        output_dir.mkdir(parents=True)
        (output_dir / "args.csv").write_text("arg-id,argument\nA1,test\n", encoding="utf-8")
        (output_dir / "hierarchical_status.json").write_text(
            json.dumps(
                {
                    "completed_jobs": [
                        {
                            "step": "extraction",
                            "params": {
                                "limit": 1000,
                                "workers": 3,
                                "prompt": "",
                                "model": "dummy",
                                "properties": [],
                            },
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )

        orchestrator = PipelineOrchestrator.from_dict(
            config={
                "name": "demo",
                "input": "demo",
                "question": "Test?",
                "provider": "local",
                "model": "dummy",
                "extraction": {"limit": 1000, "workers": 3, "prompt": "", "model": "dummy", "properties": []},
            },
            output_dir="demo",
            output_base_dir=tmp_path / "outputs",
            input_base_dir=tmp_path / "inputs",
        )

        extraction_plan = next(step for step in orchestrator.get_plan() if step["step"] == "extraction")
        assert extraction_plan["run"] is False
        assert extraction_plan["reason"] == "nothing changed"
        assert "previous" in orchestrator.config

    def test_from_dict_prefers_legacy_without_html_key(self, tmp_path):
        """Test from_dict reconciles conflicting without_html variants."""
        from analysis_core import PipelineOrchestrator

        orchestrator = PipelineOrchestrator.from_dict(
            config={
                "name": "demo",
                "input": "demo",
                "question": "Test?",
                "provider": "local",
                "model": "dummy",
                "without_html": False,
                "without-html": True,
            },
            output_dir="demo",
            output_base_dir=tmp_path / "outputs",
            input_base_dir=tmp_path / "inputs",
        )

        assert orchestrator.config["without-html"] is True
        assert orchestrator.config["without_html"] is True

    def test_run_workflow_persists_status_file(self, tmp_path, monkeypatch):
        """Test workflow mode writes hierarchical_status.json with completed jobs."""
        from analysis_core import PipelineOrchestrator
        from analysis_core.plugin import StepOutputs
        from analysis_core.workflow.definition import StepResult as WorkflowStepResult
        from analysis_core.workflow.definition import WorkflowResult

        config = {
            "name": "demo",
            "input": "demo",
            "question": "Test?",
            "provider": "local",
            "model": "dummy",
            "extraction": {},
        }

        orchestrator = PipelineOrchestrator.from_dict(
            config=config,
            output_dir="demo",
            output_base_dir=tmp_path / "outputs",
            input_base_dir=tmp_path / "inputs",
        )

        class FakeEngine:
            def run(self, workflow, config, ctx, on_step_start=None, on_step_complete=None, skip_steps=None):
                result = WorkflowResult(
                    workflow_id="test",
                    total_token_usage=12,
                    total_token_input=5,
                    total_token_output=7,
                )
                step_result = WorkflowStepResult(
                    step_id="extraction",
                    success=True,
                    outputs=StepOutputs(
                        artifacts={"arguments": ctx.output_dir / "args.csv"},
                        token_usage=12,
                        token_input=5,
                        token_output=7,
                    ),
                )
                if on_step_start:
                    on_step_start("extraction")
                if on_step_complete:
                    on_step_complete("extraction", step_result)
                result.step_results["extraction"] = step_result
                return result

        monkeypatch.setattr("analysis_core.workflow.WorkflowEngine", FakeEngine)

        result = orchestrator.run_workflow()

        assert result.success is True
        status_path = tmp_path / "outputs" / "demo" / "hierarchical_status.json"
        assert status_path.exists()

        status_data = json.loads(status_path.read_text(encoding="utf-8"))
        assert status_data["status"] == "completed"
        assert status_data["total_token_usage"] == 12
        assert status_data["token_usage_input"] == 5
        assert status_data["token_usage_output"] == 7
        assert len(status_data["completed_jobs"]) == 1
        assert status_data["completed_jobs"][0]["step"] == "extraction"

    def test_run_workflow_carries_forward_previously_completed_jobs(self, tmp_path, monkeypatch):
        """Test workflow mode preserves older completed jobs in previously_completed_jobs."""
        from analysis_core import PipelineOrchestrator
        from analysis_core.plugin import StepOutputs
        from analysis_core.workflow.definition import StepResult as WorkflowStepResult
        from analysis_core.workflow.definition import WorkflowResult

        output_dir = tmp_path / "outputs" / "demo"
        output_dir.mkdir(parents=True)
        (output_dir / "hierarchical_status.json").write_text(
            json.dumps(
                {
                    "completed_jobs": [
                        {"step": "extraction", "params": {}},
                        {"step": "embedding", "params": {}},
                    ]
                }
            ),
            encoding="utf-8",
        )

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
                    step_id="embedding",
                    success=True,
                    outputs=StepOutputs(artifacts={"embeddings": ctx.output_dir / "embeddings.pkl"}),
                )
                if on_step_start:
                    on_step_start("embedding")
                if on_step_complete:
                    on_step_complete("embedding", step_result)
                result.step_results["embedding"] = step_result
                return result

        monkeypatch.setattr("analysis_core.workflow.WorkflowEngine", FakeEngine)

        orchestrator.run_workflow()

        status_data = json.loads((output_dir / "hierarchical_status.json").read_text(encoding="utf-8"))
        assert any(job["step"] == "embedding" for job in status_data["completed_jobs"])
        assert any(job["step"] == "extraction" for job in status_data["previously_completed_jobs"])
