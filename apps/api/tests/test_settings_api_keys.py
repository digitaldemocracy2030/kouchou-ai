import os
import subprocess
import sys
from pathlib import Path

API_DIR = Path(__file__).resolve().parent.parent


def _load_settings(tmp_path, **env_vars):
    code = """
import os
from src.config import settings
print(repr(settings.OPENAI_API_KEY), repr(os.environ.get("OPENAI_API_KEY")), os.environ.get("GEMINI_API_KEY"))
"""
    env = {k: v for k, v in os.environ.items() if k not in ("OPENAI_API_KEY", "GEMINI_API_KEY")}
    pythonpath = os.pathsep.join(filter(None, [str(API_DIR), env.get("PYTHONPATH")]))
    env.update(
        {
            "PYTHONPATH": pythonpath,
            "ENV_FILE": str(tmp_path / "missing.env"),
            "ADMIN_API_KEY": "admin",
            "PUBLIC_API_KEY": "public",
            **env_vars,
        }
    )
    return subprocess.run([sys.executable, "-c", code], cwd=tmp_path, env=env, capture_output=True, text=True)


def test_api_starts_without_openai_key_for_gemini_only_setup(tmp_path):
    result = _load_settings(tmp_path, GEMINI_API_KEY="gemini-key")
    assert result.returncode == 0, result.stderr
    assert result.stdout.split() == ["None", "None", "gemini-key"]


def test_openai_key_is_exported_for_analysis_core(tmp_path):
    result = _load_settings(tmp_path, OPENAI_API_KEY="sk-test")
    assert result.returncode == 0, result.stderr
    assert result.stdout.split()[:2] == ["'sk-test'", "'sk-test'"]
