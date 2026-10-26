"""scripts/check_report_secret_leak.py と scripts/scrub_report_secrets.py のテスト。"""

import importlib.util
import json
import os
import socket
import subprocess
import sys
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
SECRET = "sk-proj-THIS-IS-A-LEAKED-USER-KEY-1234"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS_DIR / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module  # dataclass が sys.modules から module を引くため
    spec.loader.exec_module(module)
    return module


check = _load("check_report_secret_leak")
scrub = _load("scrub_report_secrets")


def _leaked_result():
    return {
        "arguments": [{"arg_id": "A1_0", "argument": "意見", "x": 0.1, "y": 0.2}],
        "clusters": [{"level": 1, "id": "1_0", "label": "ラベル", "takeaway": "要約", "value": 1, "parent": "0"}],
        "comments": {},
        "propertyMap": {},
        "translations": {},
        "overview": "概要",
        "config": {
            "question": "問い",
            "model": "gpt-4o-mini",
            "user_api_key": SECRET,
            "_output_base_dir": "/app/broadlistening/pipeline/outputs",
            "previous": {"user_api_key": SECRET, "error_stack_trace": "Traceback ...", "question": "旧"},
            "hierarchical_aggregation": {"hidden_properties": {}},
        },
        "comment_num": 1,
    }


@pytest.fixture
def report_dir(tmp_path):
    root = tmp_path / "outputs"
    for slug, result in {"leaked": _leaked_result(), "clean": {"config": {"question": "q"}, "overview": "o"}}.items():
        (root / slug).mkdir(parents=True)
        (root / slug / "hierarchical_result.json").write_text(
            json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    return root


def test_check_detects_leak_in_file_and_masks_key(report_dir, capsys):
    assert check.main([str(report_dir / "leaked" / "hierarchical_result.json")]) == 1
    out = capsys.readouterr().out
    assert "[LEAK]" in out
    assert SECRET not in out
    assert check.main([str(report_dir / "clean" / "hierarchical_result.json")]) == 0


def test_check_detects_leak_in_rsc_html():
    # Next.js は props を JSON 文字列として JS に埋め込むので、引用符が \" にエスケープされる
    payload = json.dumps(json.dumps({"result": _leaked_result()}, ensure_ascii=False))
    html = f"<html><script>self.__next_f.push([1,{payload}])</script></html>"
    finding = check.Finding(target="page")
    check.scan_html(html, finding)
    assert finding.leaked
    assert {v for _, v in finding.leaked_keys} == {SECRET}


def test_check_api_mode_lists_all_public_reports(capsys):
    reports = {"leaked": _leaked_result(), "clean": {"config": {"question": "q"}}}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            if self.headers.get("x-api-key") != "public-key":
                self.send_response(401)
                self.end_headers()
                return
            if self.path == "/reports":
                body = [{"slug": s} for s in reports]
            else:
                body = reports[self.path.rsplit("/", 1)[-1]]
            data = json.dumps(body).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        base = f"http://127.0.0.1:{server.server_port}"
        assert check.main(["--api-base", base, "--api-key", "public-key", "--all"]) == 1
    finally:
        server.shutdown()
    out = capsys.readouterr().out
    assert "漏洩あり 1 件" in out
    assert SECRET not in out


def test_scrub_dry_run_does_not_modify(report_dir, capsys):
    before = (report_dir / "leaked" / "hierarchical_result.json").read_bytes()
    assert scrub.main(["--report-dir", str(report_dir)]) == 0
    assert (report_dir / "leaked" / "hierarchical_result.json").read_bytes() == before
    assert "要修正 1 件" in capsys.readouterr().out


def test_scrub_apply_preserves_report_and_backs_up(report_dir, tmp_path):
    backup = tmp_path / "backup"
    assert scrub.main(["--report-dir", str(report_dir), "--apply", "--backup-dir", str(backup)]) == 0

    path = report_dir / "leaked" / "hierarchical_result.json"
    after = json.loads(path.read_text(encoding="utf-8"))
    original = _leaked_result()
    assert SECRET not in path.read_text(encoding="utf-8")
    # config 以外は完全に同じ、config は非公開キーだけが消える
    assert {k: v for k, v in after.items() if k != "config"} == {k: v for k, v in original.items() if k != "config"}
    assert after["config"] == {
        "question": "問い",
        "model": "gpt-4o-mini",
        "previous": {"question": "旧"},
        "hierarchical_aggregation": {"hidden_properties": {}},
    }
    assert list(after.keys()) == list(original.keys())

    backups = list(backup.glob("*/leaked/hierarchical_result.json"))
    assert len(backups) == 1
    assert SECRET in backups[0].read_text(encoding="utf-8")
    assert oct(backups[0].stat().st_mode & 0o777) == "0o600"

    # 修正済みのレポートは再実行しても対象にならない
    assert check.main(["--report-dir", str(report_dir)]) == 0


def test_scrub_refuses_backup_inside_report_dir(report_dir):
    with pytest.raises(SystemExit):
        scrub.main(["--report-dir", str(report_dir), "--apply", "--backup-dir", str(report_dir / "bak")])


def test_scrub_sync_requires_apply(report_dir):
    with pytest.raises(SystemExit):
        scrub.main(["--report-dir", str(report_dir), "--sync-storage"])


def _leaked_status():
    return {
        "output_dir": "leaked",
        "_output_base_dir": "/app/broadlistening/pipeline/outputs",
        "status": "error",
        "user_api_key": SECRET,
        "error_stack_trace": "Traceback ...",
        "previous": {"user_api_key": SECRET, "status": "completed"},
        "completed_jobs": [{"step": "extraction"}],
    }


@pytest.fixture
def report_dir_with_status(report_dir):
    (report_dir / "leaked" / "hierarchical_status.json").write_text(
        json.dumps(_leaked_status(), indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (report_dir / "clean" / "hierarchical_status.json").write_text(
        json.dumps({"output_dir": "clean", "status": "completed"}), encoding="utf-8"
    )
    return report_dir


def test_check_report_dir_also_scans_status_files(report_dir_with_status, capsys):
    (report_dir_with_status / "leaked" / "hierarchical_result.json").write_text(
        json.dumps({"config": {"question": "q"}}), encoding="utf-8"
    )
    assert check.main(["--report-dir", str(report_dir_with_status)]) == 1
    out = capsys.readouterr().out
    assert f"[LEAK]  {report_dir_with_status / 'leaked' / 'hierarchical_status.json'}" in out
    assert SECRET not in out


def test_scrub_apply_removes_user_api_key_from_status(report_dir_with_status, tmp_path, capsys):
    backup = tmp_path / "backup"
    assert scrub.main(["--report-dir", str(report_dir_with_status), "--apply", "--backup-dir", str(backup)]) == 0
    assert "要修正 2 件" in capsys.readouterr().out

    status_path = report_dir_with_status / "leaked" / "hierarchical_status.json"
    after = json.loads(status_path.read_text(encoding="utf-8"))
    expected = _leaked_status()
    del expected["user_api_key"]
    del expected["previous"]["user_api_key"]
    # status では実行時の情報（内部パス・スタックトレース）は残し、キーだけを消す
    assert after == expected
    assert list(after.keys()) == list(expected.keys())

    backups = list(backup.glob("*/leaked/hierarchical_status.json"))
    assert len(backups) == 1
    assert SECRET in backups[0].read_text(encoding="utf-8")
    assert check.main(["--report-dir", str(report_dir_with_status)]) == 0


def test_scrub_slug_covers_status_without_result(tmp_path):
    root = tmp_path / "outputs"
    (root / "running").mkdir(parents=True)
    status_path = root / "running" / "hierarchical_status.json"
    status_path.write_text(json.dumps(_leaked_status()), encoding="utf-8")

    assert scrub.main(["--report-dir", str(root), "--slug", "running", "--apply", "--no-backup"]) == 0
    assert SECRET not in status_path.read_text(encoding="utf-8")


# --- --sync-storage / --revalidate（API の src を使う経路）---
# 実際の Azure や公開ビューアには繋がず、作業ディレクトリに偽の src パッケージを置いて確かめる。

_FAKE_SRC = {
    "src/__init__.py": "",
    "src/config.py": """
import os
from pathlib import Path


class _Settings:
    REPORT_DIR = Path(os.environ["FAKE_REPORT_DIR"])
    REVALIDATE_URL = os.environ["FAKE_REVALIDATE_URL"]
    REVALIDATE_SECRET = "revalidate-secret-for-test"


settings = _Settings()
""",
    "src/services/__init__.py": "",
    "src/services/storage.py": """
import os


class _FakeStorage:
    def upload_file(self, local_path, remote_path):
        with open(os.environ["FAKE_UPLOAD_LOG"], "a", encoding="utf-8") as f:
            f.write(remote_path + "\\n")
        return True


def get_storage_service():
    return _FakeStorage()
""",
}


def _start_revalidate_server(status_code):
    requests_seen = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802
            length = int(self.headers.get("Content-Length", 0))
            requests_seen.append(json.loads(self.rfile.read(length)))
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b"{}")

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server, requests_seen


def _unused_local_url():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    return f"http://127.0.0.1:{port}/api/revalidate"


def _run_scrub_as_script(cwd, report_dir, revalidate_url, *extra):
    """``python scripts/scrub_report_secrets.py ...`` と同じく、sys.path[0] が scripts/ の状態で動かす。"""
    for rel, body in _FAKE_SRC.items():
        (cwd / rel).parent.mkdir(parents=True, exist_ok=True)
        (cwd / rel).write_text(body, encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    env.update(
        FAKE_REPORT_DIR=str(report_dir),
        FAKE_REVALIDATE_URL=revalidate_url,
        FAKE_UPLOAD_LOG=str(cwd / "uploads.log"),
    )
    return subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "scrub_report_secrets.py"), "--report-dir", str(report_dir), *extra],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_scrub_sync_storage_and_revalidate_with_report_dir(report_dir_with_status, tmp_path):
    cwd = tmp_path / "api"
    cwd.mkdir()
    server, seen = _start_revalidate_server(200)
    try:
        url = f"http://127.0.0.1:{server.server_port}/api/revalidate"
        proc = _run_scrub_as_script(
            cwd, report_dir_with_status, url, "--apply", "--no-backup", "--sync-storage", "--revalidate"
        )
    finally:
        server.shutdown()

    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "ModuleNotFoundError" not in proc.stderr
    uploaded = (cwd / "uploads.log").read_text(encoding="utf-8").split()
    assert sorted(uploaded) == ["outputs/leaked/hierarchical_result.json", "outputs/leaked/hierarchical_status.json"]
    # キャッシュ破棄は公開される結果ファイルの分だけ
    assert [r["tag"] for r in seen] == ["report-leaked"]
    assert "エラー 0 件" in proc.stdout
    assert SECRET not in (report_dir_with_status / "leaked" / "hierarchical_result.json").read_text(encoding="utf-8")


@pytest.mark.parametrize("failure", ["http_401", "unreachable"])
def test_scrub_revalidate_failure_is_reported_as_error(report_dir, tmp_path, failure):
    cwd = tmp_path / "api"
    cwd.mkdir()
    server = None
    if failure == "http_401":
        server, _ = _start_revalidate_server(401)
        url = f"http://127.0.0.1:{server.server_port}/api/revalidate"
    else:
        url = _unused_local_url()
    try:
        proc = _run_scrub_as_script(cwd, report_dir, url, "--apply", "--no-backup", "--revalidate")
    finally:
        if server is not None:
            server.shutdown()

    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "[ERROR] leaked: キャッシュ破棄に失敗（ファイルは修正済み）" in proc.stdout
    assert "-> キャッシュを破棄" not in proc.stdout
    assert "エラー 1 件" in proc.stdout
    # ファイル自体の修正は済んでいる
    assert SECRET not in (report_dir / "leaked" / "hierarchical_result.json").read_text(encoding="utf-8")


def test_scrub_sync_storage_without_api_src_exits_with_message(report_dir, tmp_path):
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    proc = subprocess.run(
        [sys.executable, str(SCRIPTS_DIR / "scrub_report_secrets.py"), "--report-dir", str(report_dir)]
        + ["--apply", "--no-backup", "--sync-storage"],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 2
    assert "apps/api（src/ がある場所）で実行してください" in proc.stderr
    assert "Traceback" not in proc.stderr
    # import できないと分かった時点で止め、ファイルは書き換えない
    assert SECRET in (report_dir / "leaked" / "hierarchical_result.json").read_text(encoding="utf-8")
