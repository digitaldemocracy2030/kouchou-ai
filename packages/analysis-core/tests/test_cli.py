"""Tests for CLI entry point."""

import json
import subprocess
import sys

import pytest


class TestCLI:
    """Test CLI functionality."""

    def test_cli_help(self):
        """Test CLI --help option."""
        result = subprocess.run(
            [sys.executable, "-m", "analysis_core", "--help"],
            capture_output=True,
            text=True,
            cwd="/Users/nishio/kouchou-ai/packages/analysis-core",
        )
        assert result.returncode == 0
        assert "kouchou-analyze" in result.stdout
        assert "--config" in result.stdout
        assert "--force" in result.stdout
        assert "--only" in result.stdout
        assert "--dry-run" in result.stdout

    def test_cli_version(self):
        """Test CLI --version option."""
        result = subprocess.run(
            [sys.executable, "-m", "analysis_core", "--version"],
            capture_output=True,
            text=True,
            cwd="/Users/nishio/kouchou-ai/packages/analysis-core",
        )
        assert result.returncode == 0
        assert "kouchou-analyze" in result.stdout
        assert "0.1.0" in result.stdout

    def test_cli_missing_config(self):
        """Test CLI fails with missing config file."""
        result = subprocess.run(
            [sys.executable, "-m", "analysis_core", "--config", "nonexistent.json"],
            capture_output=True,
            text=True,
            cwd="/Users/nishio/kouchou-ai/packages/analysis-core",
        )
        assert result.returncode == 1
        assert "Config file not found" in result.stderr

    def test_cli_dry_run(self, tmp_path):
        """Test CLI --dry-run shows plan without execution."""
        # Create config file
        config_path = tmp_path / "test_config.json"
        config_path.write_text(json.dumps({
            "input": "test",
            "question": "Test question?",
            "provider": "openai",
        }))

        # Create input directory
        input_dir = tmp_path / "inputs"
        input_dir.mkdir()

        # Create output directory
        output_dir = tmp_path / "outputs"

        result = subprocess.run(
            [
                sys.executable, "-m", "analysis_core",
                "--config", str(config_path),
                "--dry-run",
                "--input-dir", str(input_dir),
                "--output-dir", str(output_dir),
            ],
            capture_output=True,
            text=True,
            cwd="/Users/nishio/kouchou-ai/packages/analysis-core",
        )
        assert result.returncode == 0
        assert "Execution Plan" in result.stdout
        assert "extraction" in result.stdout
        assert "embedding" in result.stdout
