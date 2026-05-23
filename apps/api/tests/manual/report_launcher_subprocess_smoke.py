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

import hashlib
import json
import multiprocessing
import os
import socket
import subprocess
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
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
        pytest.skip("analysis-core virtualenv is missing. Run `cd packages/analysis-core && rye sync` first.")

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


def _fake_embedding(text: str, dimensions: int = 8) -> list[float]:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    values = []
    for index in range(dimensions):
        chunk = digest[index * 4 : (index + 1) * 4]
        if len(chunk) < 4:
            chunk = chunk.ljust(4, b"\0")
        values.append(round(int.from_bytes(chunk, "big") / 2**32, 6))
    return values


def _extracted_opinion(text: str) -> str:
    normalized = " ".join(text.split()).strip()
    if not normalized:
        return "意見なし"
    first_sentence = normalized.split("。")[0].strip()
    return first_sentence or normalized


def _label_payload(text: str) -> dict[str, str]:
    lines = [line.strip(" -#") for line in text.splitlines() if line.strip()]
    seed = lines[0] if lines else "意見群"
    label = seed[:20]
    return {
        "label": label,
        "description": f"{label}に関する意見のまとまり",
    }


def _overview_payload(text: str) -> dict[str, str]:
    cluster_count = text.count("# Cluster ")
    if cluster_count == 0:
        cluster_count = 1
    return {
        "summary": f"{cluster_count}件の主要論点が確認された。ローカル偽 LLM による通常フロー smoke test。",
    }


def _chat_completion_response(payload: dict) -> dict:
    messages = payload.get("messages", [])
    user_content = messages[-1].get("content", "") if messages else ""
    response_format = payload.get("response_format", {})
    schema_name = response_format.get("json_schema", {}).get("name")

    if schema_name == "ExtractionResponse":
        content = json.dumps(
            {"extractedOpinionList": [_extracted_opinion(user_content)]},
            ensure_ascii=False,
        )
    elif schema_name == "LabellingFromat":
        content = json.dumps(_label_payload(user_content), ensure_ascii=False)
    elif schema_name == "OverviewResponse":
        content = json.dumps(_overview_payload(user_content), ensure_ascii=False)
    else:
        content = json.dumps({"message": "ok"}, ensure_ascii=False)

    prompt_tokens = max(1, len(json.dumps(messages, ensure_ascii=False)) // 20)
    completion_tokens = max(1, len(content) // 20)

    return {
        "id": "chatcmpl-fake-local",
        "object": "chat.completion",
        "created": 0,
        "model": payload.get("model", "manual-smoke-model"),
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
    }


def _embedding_response(payload: dict) -> dict:
    inputs = payload.get("input", [])
    if isinstance(inputs, str):
        inputs = [inputs]

    return {
        "object": "list",
        "data": [
            {
                "object": "embedding",
                "index": index,
                "embedding": _fake_embedding(text),
            }
            for index, text in enumerate(inputs)
        ],
        "model": payload.get("model", "text-embedding-3-small"),
        "usage": {
            "prompt_tokens": len(inputs),
            "total_tokens": len(inputs),
        },
    }


def _serve_fake_local_llm(port: int) -> None:
    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.0"

        def do_POST(self):  # noqa: N802
            content_length = int(self.headers.get("Content-Length", "0"))
            raw_body = self.rfile.read(content_length).decode("utf-8")
            payload = json.loads(raw_body or "{}")

            if self.path == "/v1/chat/completions":
                response = _chat_completion_response(payload)
                _send_json(self, 200, response)
                return

            if self.path == "/v1/embeddings":
                response = _embedding_response(payload)
                _send_json(self, 200, response)
                return

            _send_json(self, 404, {"error": f"Unsupported path: {self.path}"})

        def log_message(self, *_args, **_kwargs):
            return

    with HTTPServer(("127.0.0.1", port), Handler) as httpd:
        httpd.serve_forever(poll_interval=0.1)


def _send_json(handler: BaseHTTPRequestHandler, status_code: int, payload: dict) -> None:
    encoded = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status_code)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(encoded)))
    handler.send_header("Connection", "close")
    handler.end_headers()
    handler.wfile.write(encoded)


class LocalLLMServerProcess:
    """Run a tiny OpenAI-compatible fake server in a child process."""

    def __init__(self) -> None:
        self.port = self._reserve_port()
        self._process: multiprocessing.Process | None = None

    @property
    def address(self) -> str:
        return f"127.0.0.1:{self.port}"

    def __enter__(self) -> "LocalLLMServerProcess":
        self._process = multiprocessing.Process(target=_serve_fake_local_llm, args=(self.port,), daemon=True)
        self._process.start()
        self._wait_until_ready()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._process is None:
            return
        if self._process.is_alive():
            self._process.terminate()
            self._process.join(timeout=5)
        if self._process.is_alive():
            self._process.kill()
            self._process.join(timeout=5)

    @staticmethod
    def _reserve_port() -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))
            return int(sock.getsockname()[1])

    def _wait_until_ready(self) -> None:
        for _ in range(50):
            if self._process is not None and not self._process.is_alive():
                raise RuntimeError("fake local LLM process exited before becoming ready")
            try:
                with socket.create_connection(("127.0.0.1", self.port), timeout=0.1):
                    return
            except OSError:
                time.sleep(0.1)
        raise RuntimeError("fake local LLM process did not become ready")


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


def _full_flow_report_input(local_llm_address: str):
    from src.schemas.admin_report import Comment, Prompt, ReportInput

    return ReportInput(
        input="manual-full-subprocess-smoke",
        question="通常フロー smoke test",
        intro="Fake local LLM smoke test",
        cluster=[2],
        model="manual-smoke-model",
        workers=1,
        prompt=Prompt(
            extraction="コメントから意見を1件抽出してください。",
            initial_labelling="クラスタのラベルと説明を返してください。",
            merge_labelling="上位クラスタのラベルと説明を返してください。",
            overview="全体概要を要約してください。",
        ),
        comments=[
            Comment(id="1", comment="医療分野でAI活用をもっと進めてほしい。"),
            Comment(id="2", comment="再生可能エネルギーへの投資を増やすべきだ。"),
            Comment(id="3", comment="地方の教育格差を埋めるためにオンライン学習を強化したい。"),
            Comment(id="4", comment="介護現場ではロボット支援の導入が必要だ。"),
            Comment(id="5", comment="プライバシー保護のルール整備を急いでほしい。"),
        ],
        is_pubcom=False,
        provider="local",
        local_llm_address=local_llm_address,
        is_embedded_at_local=False,
        enable_source_link=False,
    )


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


def test_launch_report_generation_runs_full_analysis_core_subprocess(monkeypatch, tmp_path):
    from src.services import report_launcher, report_status

    slug = "manual-full-subprocess-smoke"
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
    report_status._report_status.clear()

    with LocalLLMServerProcess() as fake_llm:
        report_input = _full_flow_report_input(fake_llm.address)
        report_launcher.launch_report_generation(report_input)

    output_dir = report_dir / slug
    result_path = output_dir / "hierarchical_result.json"
    status_path = output_dir / "hierarchical_status.json"
    log_path = output_dir / report_launcher.ANALYSIS_LOG_FILENAME
    args_path = output_dir / "args.csv"
    embeddings_path = output_dir / "embeddings.pkl"

    assert result_path.exists()
    assert status_path.exists()
    assert log_path.exists()
    assert args_path.exists()
    assert embeddings_path.exists()

    result_data = json.loads(result_path.read_text(encoding="utf-8"))
    status_data = json.loads(status_path.read_text(encoding="utf-8"))
    updated = report_status._report_status[slug]

    assert result_data["comment_num"] == 5
    assert len(result_data["arguments"]) >= 5
    assert len(result_data["clusters"]) >= 3
    assert "主要論点" in result_data["overview"]
    assert result_data["config"]["provider"] == "local"
    assert result_data["config"]["model"] == "manual-smoke-model"
    assert "Fake local LLM smoke test" in result_data["config"]["intro"]

    assert status_data["status"] == "completed"
    assert [job["step"] for job in status_data["completed_jobs"]] == [
        "extraction",
        "embedding",
        "hierarchical_clustering",
        "hierarchical_initial_labelling",
        "hierarchical_merge_labelling",
        "hierarchical_overview",
        "hierarchical_aggregation",
    ]
    assert status_data["total_token_usage"] > 0
    assert status_data["token_usage_input"] > 0
    assert status_data["token_usage_output"] > 0

    assert updated["status"] == "ready"
    assert updated["provider"] == "local"
    assert updated["model"] == "manual-smoke-model"
    assert updated["token_usage"] > 0
    assert updated["token_usage_input"] > 0
    assert updated["token_usage_output"] > 0
