import os
import subprocess
import sys

import pytest


@pytest.fixture
def project_dir(tmp_path):
    """A user project whose .env sits in a parent of the working directory."""
    project = tmp_path / "project"
    workdir = project / "reports"
    workdir.mkdir(parents=True)
    (project / ".env").write_text("OPENAI_API_KEY=sk-from-project-dotenv\nLLM_REQUEST_TIMEOUT_SECONDS=613\n")
    return workdir


def _run(code, cwd):
    # Run as a script file like the CLI: with `python -c`, python-dotenv treats the
    # session as interactive and searches from the working directory anyway.
    script = cwd.parent.parent / "check_env.py"
    script.write_text(code)
    env = {k: v for k, v in os.environ.items() if k not in ("OPENAI_API_KEY", "LLM_REQUEST_TIMEOUT_SECONDS")}
    return subprocess.run([sys.executable, str(script)], cwd=cwd, env=env, capture_output=True, text=True)


def test_import_time_settings_come_from_working_directory_dotenv(project_dir):
    code = """
import os
from analysis_core.services import llm  # noqa: F401
from analysis_core.services.timeouts import DEFAULT_REQUEST_TIMEOUT_SECONDS
assert DEFAULT_REQUEST_TIMEOUT_SECONDS == 613, DEFAULT_REQUEST_TIMEOUT_SECONDS
assert os.environ["OPENAI_API_KEY"] == "sk-from-project-dotenv"
"""
    result = _run(code, project_dir)
    assert result.returncode == 0, result.stderr


def test_validate_api_keys_reads_working_directory_dotenv(project_dir):
    code = """
from analysis_core.core.orchestration import validate_api_keys
validate_api_keys("openai")
"""
    result = _run(code, project_dir)
    assert result.returncode == 0, result.stderr
