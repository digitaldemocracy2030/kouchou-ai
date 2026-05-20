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
