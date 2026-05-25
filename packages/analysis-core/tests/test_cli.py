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
        assert "--reuse-from" in result.stdout

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
        (input_dir / "test.csv").write_text("comment-id,comment-body\n1,test\n", encoding="utf-8")

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
        assert "Preflight validation passed." in result.stdout
        assert "Execution Plan" in result.stdout
        assert "extraction" in result.stdout
        assert "embedding" in result.stdout
        assert not (output_dir / "test_config" / "hierarchical_status.json").exists()

    def test_cli_dry_run_with_reuse_from_skips_seeded_steps(self, tmp_path):
        """Test CLI --reuse-from seeds previous artifacts for comparison runs."""
        config_path = tmp_path / "test_config.json"
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
        input_dir.mkdir()
        (input_dir / "test.csv").write_text("comment-id,comment-body\n1,test\n", encoding="utf-8")

        output_dir = tmp_path / "outputs"
        source_dir = output_dir / "baseline"
        source_dir.mkdir(parents=True)
        (source_dir / "args.csv").write_text("arg-id,argument\nA1,test\n", encoding="utf-8")
        (source_dir / "relations.csv").write_text("arg-id,comment-id\nA1,1\n", encoding="utf-8")
        (source_dir / "embeddings.pkl").write_bytes(b"pickle-placeholder")
        (source_dir / "hierarchical_status.json").write_text(
            json.dumps(
                {
                    "status": "completed",
                    "completed_jobs": [
                        {"step": "extraction", "params": {"limit": 1000}},
                        {"step": "embedding", "params": {"model": "text-embedding-3-small"}},
                    ],
                }
            ),
            encoding="utf-8",
        )

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "analysis_core",
                "--config",
                str(config_path),
                "--dry-run",
                "--reuse-from",
                "baseline",
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
        assert "Seeded outputs for test_config from baseline: extraction, embedding" in result.stdout
        assert "[SKIP] extraction: nothing changed" in result.stdout
        assert "[SKIP] embedding: nothing changed" in result.stdout

    def test_cli_validate_config(self, tmp_path):
        """Test standalone config validation mode."""
        config_path = tmp_path / "test_config.json"
        config_path.write_text(json.dumps({"input": "test", "question": "Test question?", "provider": "openai"}))

        result = subprocess.run(
            [sys.executable, "-m", "analysis_core", "--config", str(config_path), "--validate-config"],
            capture_output=True,
            text=True,
            cwd=PACKAGE_ROOT,
        )

        assert result.returncode == 0
        assert "Preflight validation passed." in result.stdout
        assert "Config:" in result.stdout

    def test_cli_validate_input(self, tmp_path):
        """Test standalone input validation mode."""
        config_path = tmp_path / "test_config.json"
        config_path.write_text(json.dumps({"input": "demo", "question": "Test question?", "provider": "openai"}))
        input_dir = tmp_path / "inputs"
        input_dir.mkdir()
        (input_dir / "demo.csv").write_text("comment-id,comment-body\n1,test\n", encoding="utf-8")

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "analysis_core",
                "--config",
                str(config_path),
                "--validate-input",
                "--input-dir",
                str(input_dir),
            ],
            capture_output=True,
            text=True,
            cwd=PACKAGE_ROOT,
        )

        assert result.returncode == 0
        assert "Preflight validation passed." in result.stdout
        assert "Input:" in result.stdout

    def test_cli_validate_input_reports_missing_columns(self, tmp_path):
        """Test input validation reports a useful CSV schema error."""
        config_path = tmp_path / "test_config.json"
        config_path.write_text(json.dumps({"input": "demo", "question": "Test question?", "provider": "openai"}))
        input_dir = tmp_path / "inputs"
        input_dir.mkdir()
        (input_dir / "demo.csv").write_text("comment-id,text\n1,test\n", encoding="utf-8")

        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "analysis_core",
                "--config",
                str(config_path),
                "--validate-input",
                "--input-dir",
                str(input_dir),
            ],
            capture_output=True,
            text=True,
            cwd=PACKAGE_ROOT,
        )

        assert result.returncode == 1
        assert "missing required columns" in result.stderr

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

    def test_cli_duplicate_style_rerun_reuses_artifacts_and_restarts_from_overview(self, monkeypatch, tmp_path, capsys):
        """Test duplicate/reuse style reruns only restart the missing downstream steps."""
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
                    "embedding": {
                        "model": "text-embedding-3-small",
                    },
                    "hierarchical_clustering": {
                        "cluster_nums": [2, 4],
                    },
                    "hierarchical_initial_labelling": {
                        "sampling_num": 3,
                        "workers": 1,
                        "prompt": "",
                        "model": "gpt-4o-mini",
                    },
                    "hierarchical_merge_labelling": {
                        "sampling_num": 3,
                        "workers": 1,
                        "prompt": "",
                        "model": "gpt-4o-mini",
                    },
                    "hierarchical_overview": {
                        "prompt": "",
                        "model": "gpt-4o-mini",
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
        for filename in (
            "args.csv",
            "embeddings.pkl",
            "hierarchical_clusters.csv",
            "hierarchical_initial_labels.csv",
            "hierarchical_merge_labels.csv",
        ):
            (output_subdir / filename).write_text(filename, encoding="utf-8")
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
                        },
                        {
                            "step": "embedding",
                            "params": {
                                "model": "text-embedding-3-small",
                            },
                        },
                        {
                            "step": "hierarchical_clustering",
                            "params": {
                                "cluster_nums": [2, 4],
                            },
                        },
                        {
                            "step": "hierarchical_initial_labelling",
                            "params": {
                                "sampling_num": 3,
                                "workers": 1,
                                "prompt": "",
                                "model": "gpt-4o-mini",
                            },
                        },
                        {
                            "step": "hierarchical_merge_labelling",
                            "params": {
                                "sampling_num": 3,
                                "workers": 1,
                                "prompt": "",
                                "model": "gpt-4o-mini",
                            },
                        },
                        {
                            "step": "hierarchical_overview",
                            "params": {
                                "prompt": "",
                                "model": "gpt-4o-mini",
                            },
                        },
                        {
                            "step": "hierarchical_aggregation",
                            "params": {},
                        },
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
                    total_token_usage=17,
                    total_token_input=8,
                    total_token_output=9,
                )
                overview_result = WorkflowStepResult(
                    step_id="overview",
                    success=True,
                    outputs=StepOutputs(
                        artifacts={"overview": ctx.output_dir / "hierarchical_overview.txt"},
                        token_usage=7,
                        token_input=3,
                        token_output=4,
                    ),
                )
                aggregation_result = WorkflowStepResult(
                    step_id="aggregation",
                    success=True,
                    outputs=StepOutputs(
                        artifacts={"result": ctx.output_dir / "hierarchical_result.json"},
                        token_usage=10,
                        token_input=5,
                        token_output=5,
                    ),
                )
                for step_id, step_result in (
                    ("overview", overview_result),
                    ("aggregation", aggregation_result),
                ):
                    if on_step_start:
                        on_step_start(step_id)
                    if on_step_complete:
                        on_step_complete(step_id, step_result)
                    result.step_results[step_id] = step_result
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
                "--without-html",
            ],
        )

        exit_code = __main__.main()
        captured = capsys.readouterr()

        assert exit_code == 0
        assert seen["skip_steps"] == {
            "extraction",
            "embedding",
            "clustering",
            "initial_labelling",
            "merge_labelling",
            "visualization",
        }
        assert "Pipeline completed successfully!" in captured.out

        status_data = json.loads((output_subdir / "hierarchical_status.json").read_text(encoding="utf-8"))
        assert status_data["status"] == "completed"
        assert [job["step"] for job in status_data["completed_jobs"]] == [
            "hierarchical_overview",
            "hierarchical_aggregation",
        ]
        assert {job["step"] for job in status_data["previously_completed_jobs"]} == {
            "extraction",
            "embedding",
            "hierarchical_clustering",
            "hierarchical_initial_labelling",
            "hierarchical_merge_labelling",
        }
