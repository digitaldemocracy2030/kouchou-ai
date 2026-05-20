"""Tests for CLI entry point."""

import json
import re
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock

PACKAGE_ROOT = Path(__file__).resolve().parents[1]


class TestCLI:
    """Test CLI functionality."""

    def test_cli_help(self):
        """Test CLI --help option."""
        result = subprocess.run(
            [sys.executable, "-m", "analysis_core", "--help"],
            capture_output=True,
            text=True,
            cwd=PACKAGE_ROOT,
        )
        assert result.returncode == 0
        assert "kouchou-analyze" in result.stdout
        assert "--config" in result.stdout
        assert "--force" in result.stdout
        assert "--only" in result.stdout
        assert "--dry-run" in result.stdout

    def test_cli_version(self):
        """Test CLI --version option."""
        from analysis_core import __version__

        result = subprocess.run(
            [sys.executable, "-m", "analysis_core", "--version"],
            capture_output=True,
            text=True,
            cwd=PACKAGE_ROOT,
        )
        assert result.returncode == 0
        assert re.fullmatch(r"kouchou-analyze \S+\n", result.stdout)
        assert result.stdout.strip() == f"kouchou-analyze {__version__}"

    def test_cli_missing_config(self):
        """Test CLI fails with missing config file."""
        result = subprocess.run(
            [sys.executable, "-m", "analysis_core", "--config", "nonexistent.json"],
            capture_output=True,
            text=True,
            cwd=PACKAGE_ROOT,
        )
        assert result.returncode == 1
        assert "Config file not found" in result.stderr

    def test_cli_dry_run(self, tmp_path):
        """Test CLI --dry-run shows plan without execution."""
        # Create config file
        config_path = tmp_path / "test_config.json"
        config_path.write_text(
            json.dumps(
                {
                    "input": "test",
                    "question": "Test question?",
                    "provider": "openai",
                }
            )
        )

        # Create input directory
        input_dir = tmp_path / "inputs"
        input_dir.mkdir()

        # Create output directory
        output_dir = tmp_path / "outputs"

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "analysis_core",
                "--config",
                str(config_path),
                "--dry-run",
                "--input-dir",
                str(input_dir),
                "--output-dir",
                str(output_dir),
            ],
            capture_output=True,
            text=True,
            cwd=PACKAGE_ROOT,
        )
        assert result.returncode == 0
        assert "Execution Plan" in result.stdout
        assert "extraction" in result.stdout
        assert "embedding" in result.stdout
        assert not (output_dir / "test_config" / "hierarchical_status.json").exists()

    def test_cli_uses_default_execution_path(self, monkeypatch, tmp_path, capsys):
        """Test CLI execution delegates to run_default()."""
        from analysis_core import __main__
        from analysis_core.orchestrator import PipelineResult

        config_path = tmp_path / "test_config.json"
        config_path.write_text(json.dumps({"input": "test", "question": "Test?", "provider": "local"}))

        fake_orchestrator = MagicMock()
        fake_orchestrator.output_base_dir = tmp_path / "outputs"
        fake_orchestrator.run_default.return_value = PipelineResult(
            success=True,
            total_duration_seconds=0.5,
            total_token_usage=12,
            output_dir=tmp_path / "outputs" / "test_config",
        )

        monkeypatch.setattr(__main__.PipelineOrchestrator, "from_config", lambda **kwargs: fake_orchestrator)
        monkeypatch.setattr(
            sys,
            "argv",
            ["analysis_core", "--config", str(config_path), "--output-dir", str(tmp_path / "outputs")],
        )

        exit_code = __main__.main()
        captured = capsys.readouterr()

        assert exit_code == 0
        fake_orchestrator.run_default.assert_called_once_with()
        assert "Pipeline completed successfully!" in captured.out

    def test_cli_execution_reuses_previous_status_via_workflow_plan(self, monkeypatch, tmp_path, capsys):
        """Test CLI execution carries rerun planning into the workflow engine."""
        from analysis_core import __main__
        from analysis_core.plugin import StepOutputs
        from analysis_core.workflow.definition import StepResult as WorkflowStepResult
        from analysis_core.workflow.definition import WorkflowResult

        config_path = tmp_path / "demo.json"
        config_path.write_text(
            json.dumps(
                {
                    "input": "demo",
                    "question": "Test?",
                    "provider": "local",
                    "model": "gpt-4o-mini",
                    "extraction": {
                        "limit": 1000,
                        "workers": 1,
                        "prompt": "",
                        "model": "gpt-4o-mini",
                        "properties": [],
                    },
                }
            )
        )

        input_dir = tmp_path / "inputs"
        output_dir = tmp_path / "outputs"
        input_dir.mkdir()
        (input_dir / "demo.csv").write_text("comment-id,comment-body\n1,test\n", encoding="utf-8")

        output_subdir = output_dir / "demo"
        output_subdir.mkdir(parents=True)
        (output_subdir / "args.csv").write_text("arg-id,argument\nA1,test\n", encoding="utf-8")
        (output_subdir / "hierarchical_status.json").write_text(
            json.dumps(
                {
                    "completed_jobs": [
                        {
                            "step": "extraction",
                            "params": {
                                "limit": 1000,
                                "workers": 1,
                                "prompt": "",
                                "model": "gpt-4o-mini",
                                "properties": [],
                            },
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )

        seen = {}

        class FakeEngine:
            def run(self, workflow, config, ctx, on_step_start=None, on_step_complete=None, skip_steps=None):
                seen["skip_steps"] = skip_steps
                result = WorkflowResult(
                    workflow_id="test",
                    total_token_usage=9,
                    total_token_input=4,
                    total_token_output=5,
                )
                step_result = WorkflowStepResult(
                    step_id="embedding",
                    success=True,
                    outputs=StepOutputs(
                        artifacts={"embeddings": ctx.output_dir / "embeddings.pkl"},
                        token_usage=9,
                        token_input=4,
                        token_output=5,
                    ),
                )
                if on_step_start:
                    on_step_start("embedding")
                if on_step_complete:
                    on_step_complete("embedding", step_result)
                result.step_results["embedding"] = step_result
                return result

        monkeypatch.setattr("analysis_core.workflow.WorkflowEngine", FakeEngine)
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "analysis_core",
                "--config",
                str(config_path),
                "--input-dir",
                str(input_dir),
                "--output-dir",
                str(output_dir),
            ],
        )

        exit_code = __main__.main()
        captured = capsys.readouterr()

        assert exit_code == 0
        assert seen["skip_steps"] == {"extraction"}
        assert "Pipeline completed successfully!" in captured.out

        status_data = json.loads((output_subdir / "hierarchical_status.json").read_text(encoding="utf-8"))
        assert status_data["status"] == "completed"
        assert status_data["total_token_usage"] == 9
        assert any(job["step"] == "embedding" for job in status_data["completed_jobs"])
        assert any(job["step"] == "extraction" for job in status_data["previously_completed_jobs"])
