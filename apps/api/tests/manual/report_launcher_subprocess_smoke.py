"""Manual smoke tests for the API -> subprocess -> analysis-core boundary.

These tests are intentionally kept out of default pytest collection by living in
``tests/manual/`` with a non-``test_*.py`` filename.

Run locally with the API virtualenv so the child ``python`` process resolves the
API-side dependencies, while this test rewrites ``PATH`` so the child process
uses ``packages/analysis-core/.venv/bin/python``.

    cd apps/api
    ADMIN_API_KEY=dummy PUBLIC_API_KEY=dummy OPENAI_API_KEY=dummy \
      rye run pytest tests/manual/report_launcher_subprocess_smoke.py -q -s
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.manual_smoke


class ImmediateThread:
    """Run the background monitor inline so the smoke test stays deterministic."""

    def __init__(self, target=None, args=(), kwargs=None, **_):
        self.target = target
        self.args = args
        self.kwargs = kwargs or {}

    def start(self):
        if self.target is not None:
            self.target(*self.args, **self.kwargs)


class DummyReportSyncService:
    """No-op sync service for local subprocess smoke tests."""

    def sync_report_files_to_storage(self, value):
        return value

    def sync_input_file_to_storage(self, value):
        return value

    def sync_config_file_to_storage(self, value):
        return value

    def sync_status_file_to_storage(self):
        return None


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _analysis_core_python() -> Path:
    return _repo_root() / "packages" / "analysis-core" / ".venv" / "bin" / "python"


def _prepend_analysis_core_python(monkeypatch: pytest.MonkeyPatch) -> None:
    analysis_core_python = _analysis_core_python()
    if not analysis_core_python.exists():
        pytest.skip(
            "analysis-core virtualenv is missing. Run `cd packages/analysis-core && rye sync` first."
        )

    analysis_core_bin = str(analysis_core_python.parent)
    current_path = os.environ.get("PATH", "")
    monkeypatch.setenv("PATH", f"{analysis_core_bin}{os.pathsep}{current_path}")


def _ensure_analysis_core_cli_available() -> None:
    env = os.environ.copy()
    completed = subprocess.run(
        ["python", "-m", "analysis_core", "--version"],
        capture_output=True,
        text=True,
        cwd=_repo_root() / "apps" / "api",
        env=env,
    )
    if completed.returncode != 0:
        pytest.skip(
            "analysis_core CLI is not runnable through the analysis-core virtualenv. "
            "Check `packages/analysis-core/.venv` and sync that environment first."
        )


def _write_csv(path: Path, header: str, rows: list[str]) -> None:
    path.write_text("\n".join([header, *rows]) + "\n", encoding="utf-8")


def _seed_report_status(report_status_module, slug: str) -> None:
    report_status_module._report_status.clear()
    report_status_module._report_status[slug] = {
        "slug": slug,
        "source_slug": None,
        "status": "processing",
        "title": "Smoke test report",
        "description": "Manual subprocess smoke test",
        "is_pubcom": False,
        "visibility": "unlisted",
        "created_at": "2026-05-23T00:00:00+00:00",
        "token_usage": 0,
        "token_usage_input": 0,
        "token_usage_output": 0,
        "estimated_cost": 0.0,
        "provider": "local",
        "model": "manual-smoke-model",
    }
    report_status_module.save_status()


def _seed_aggregation_inputs(report_dir: Path, input_dir: Path, slug: str) -> None:
    output_dir = report_dir / slug
    output_dir.mkdir(parents=True, exist_ok=True)

    _write_csv(
        input_dir / f"{slug}.csv",
        "comment-id,comment-body",
        ['c1,"Need more explanation for this proposal."'],
    )
    _write_csv(
        output_dir / "args.csv",
        "arg-id,argument",
        ['a1,"Need more explanation"'],
    )
    _write_csv(
        output_dir / "relations.csv",
        "arg-id,comment-id",
        ["a1,c1"],
    )
    _write_csv(
        output_dir / "hierarchical_clusters.csv",
        "arg-id,argument,x,y,cluster-level-1-id",
        ['a1,"Need more explanation",0.1,0.2,1'],
    )
    _write_csv(
        output_dir / "hierarchical_merge_labels.csv",
        "level,id,label,description,value,parent,density_rank_percentile",
        ['1,1,"説明不足","説明を求める意見が集まっている",1,0,1.0'],
    )
    (output_dir / "hierarchical_overview.txt").write_text(
        "説明不足への対応を求める小さなクラスタが観測された。",
        encoding="utf-8",
    )


def _write_config(config_dir: Path, slug: str) -> Path:
    config_path = config_dir / f"{slug}.json"
    config_path.write_text(
        json.dumps(
            {
                "input": slug,
                "question": "What should be improved?",
                "intro": "Manual subprocess smoke test",
                "provider": "local",
                "model": "manual-smoke-model",
                "is_pubcom": False,
                "is_embedded_at_local": False,
                "enable_source_link": False,
                "extraction": {
                    "limit": 1,
                    "properties": [],
                    "categories": {},
                },
                "hierarchical_aggregation": {
                    "hidden_properties": {},
                },
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return config_path


def test_execute_aggregation_launches_real_analysis_core_subprocess(monkeypatch, tmp_path):
    from src.services import report_launcher, report_status

    slug = "manual-subprocess-smoke"
    report_dir = tmp_path / "reports"
    config_dir = tmp_path / "configs"
    input_dir = tmp_path / "inputs"
    data_dir = tmp_path / "data"
    report_dir.mkdir(parents=True)
    config_dir.mkdir(parents=True)
    input_dir.mkdir(parents=True)
    data_dir.mkdir(parents=True)

    monkeypatch.setattr(report_launcher.settings, "REPORT_DIR", report_dir)
    monkeypatch.setattr(report_launcher.settings, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(report_launcher.settings, "INPUT_DIR", input_dir)
    monkeypatch.setattr(report_status.settings, "DATA_DIR", data_dir)
    monkeypatch.setattr(report_status, "STATE_FILE", data_dir / "report_status.json")
    monkeypatch.setattr(report_launcher.threading, "Thread", ImmediateThread)
    monkeypatch.setattr(report_launcher, "ReportSyncService", DummyReportSyncService)
    _prepend_analysis_core_python(monkeypatch)
    _ensure_analysis_core_cli_available()

    _seed_report_status(report_status, slug)
    _seed_aggregation_inputs(report_dir, input_dir, slug)
    _write_config(config_dir, slug)

    result = report_launcher.execute_aggregation(slug)

    assert result is True

    result_path = report_dir / slug / "hierarchical_result.json"
    status_path = report_dir / slug / "hierarchical_status.json"
    log_path = report_dir / slug / report_launcher.ANALYSIS_LOG_FILENAME
    assert result_path.exists()
    assert status_path.exists()
    assert log_path.exists()

    result_data = json.loads(result_path.read_text(encoding="utf-8"))
    status_data = json.loads(status_path.read_text(encoding="utf-8"))
    updated = report_status._report_status[slug]

    assert result_data["comment_num"] == 1
    assert len(result_data["arguments"]) == 1
    assert len(result_data["clusters"]) == 2
    assert result_data["overview"] == "説明不足への対応を求める小さなクラスタが観測された。"
    assert result_data["config"]["intro"].startswith("Manual subprocess smoke test")

    assert status_data["status"] == "completed"
    assert [job["step"] for job in status_data["completed_jobs"]] == ["hierarchical_aggregation"]
    assert status_data["total_token_usage"] == 0

    assert updated["status"] == "ready"
    assert updated["token_usage"] == 0
    assert updated["token_usage_input"] == 0
    assert updated["token_usage_output"] == 0
