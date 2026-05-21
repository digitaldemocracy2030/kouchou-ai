def test_user_api_key_propagation_to_env(monkeypatch):
    # user_api_keyが指定された場合、その値が環境変数USER_API_KEYにセットされてサブプロセスに渡ることを確認
    import subprocess
    import threading

    from src.schemas.admin_report import Prompt, ReportInput
    from src.services import report_launcher

    called = {}

    class DummyPopen:
        def __init__(self, *args, **kwargs):
            called["args"] = args[0]
            called["env"] = kwargs.get("env", {})

        def wait(self):
            return 0

    class DummyThread:
        def __init__(self, *args, **kwargs):
            pass

        def start(self):
            pass  # Don't actually start the thread

    monkeypatch.setattr(subprocess, "Popen", DummyPopen)
    monkeypatch.setattr(threading, "Thread", DummyThread)
    report_input = ReportInput(
        input="dummy",
        question="q",
        intro="i",
        model="m",
        provider="p",
        is_pubcom=False,
        is_embedded_at_local=False,
        local_llm_address=None,
        prompt=Prompt(extraction="", initial_labelling="", merge_labelling="", overview=""),
        workers=1,
        cluster=[1],
        enable_source_link=False,
        comments=[],
    )
    report_launcher.launch_report_generation(report_input, user_api_key="test-key")
    assert called["env"]["USER_API_KEY"] == "test-key"
    assert called["args"][:3] == ["python", "-m", "analysis_core"]
    assert "--without-html" in called["args"]


def test_env_user_api_key_not_set_when_user_api_key_not_provided(monkeypatch):
    # user_api_keyが指定されない場合、USER_API_KEYが環境変数にセットされずサブプロセスに渡らないことを確認
    import subprocess
    import threading

    from src.schemas.admin_report import Prompt, ReportInput
    from src.services import report_launcher

    called = {}

    class DummyPopen:
        def __init__(self, *args, **kwargs):
            called["args"] = args[0]
            called["env"] = kwargs.get("env", {})

        def wait(self):
            return 0

    class DummyThread:
        def __init__(self, *args, **kwargs):
            pass

        def start(self):
            pass  # Don't actually start the thread

    monkeypatch.setattr(subprocess, "Popen", DummyPopen)
    monkeypatch.setattr(threading, "Thread", DummyThread)
    report_input = ReportInput(
        input="dummy",
        question="q",
        intro="i",
        model="m",
        provider="p",
        is_pubcom=False,
        is_embedded_at_local=False,
        local_llm_address=None,
        prompt=Prompt(extraction="", initial_labelling="", merge_labelling="", overview=""),
        workers=1,
        cluster=[1],
        enable_source_link=False,
        comments=[],
    )
    report_launcher.launch_report_generation(report_input)
    assert "USER_API_KEY" not in called["env"]
    assert "--without-html" in called["args"]


def test_env_user_api_key_not_set_when_user_api_key_empty(monkeypatch):
    # user_api_keyが空文字列の場合、USER_API_KEYが環境変数にセットされずサブプロセスに渡らないことを確認
    import subprocess
    import threading

    from src.schemas.admin_report import Prompt, ReportInput
    from src.services import report_launcher

    called = {}

    class DummyPopen:
        def __init__(self, *args, **kwargs):
            called["args"] = args[0]
            called["env"] = kwargs.get("env", {})

        def wait(self):
            return 0

    class DummyThread:
        def __init__(self, *args, **kwargs):
            pass

        def start(self):
            pass  # Don't actually start the thread

    monkeypatch.setattr(subprocess, "Popen", DummyPopen)
    monkeypatch.setattr(threading, "Thread", DummyThread)
    report_input = ReportInput(
        input="dummy",
        question="q",
        intro="i",
        model="m",
        provider="p",
        is_pubcom=False,
        is_embedded_at_local=False,
        local_llm_address=None,
        prompt=Prompt(extraction="", initial_labelling="", merge_labelling="", overview=""),
        workers=1,
        cluster=[1],
        enable_source_link=False,
        comments=[],
    )
    report_launcher.launch_report_generation(report_input, user_api_key="")
    assert "USER_API_KEY" not in called["env"]
    assert "--without-html" in called["args"]


def test_user_api_key_propagation_to_env_in_aggregation(monkeypatch):
    # user_api_keyが指定された場合、その値が環境変数USER_API_KEYにセットされてサブプロセスに渡ることを確認（集約処理）
    import subprocess
    import threading

    from src.services import report_launcher

    called = {}

    class DummyPopen:
        def __init__(self, *args, **kwargs):
            called["args"] = args[0]
            called["env"] = kwargs.get("env", {})

        def wait(self):
            return 0

    class DummyThread:
        def __init__(self, *args, **kwargs):
            pass

        def start(self):
            pass  # Don't actually start the thread

    monkeypatch.setattr(subprocess, "Popen", DummyPopen)
    monkeypatch.setattr(threading, "Thread", DummyThread)
    result = report_launcher.execute_aggregation("slug", user_api_key="test-key")
    assert called["env"]["USER_API_KEY"] == "test-key"
    assert called["args"][-2:] == ["--only", "hierarchical_aggregation"]
    assert result is True


def test_env_user_api_key_not_set_in_aggregation_when_user_api_key_not_provided(monkeypatch):
    # user_api_keyが指定されない場合、USER_API_KEYが環境変数にセットされずサブプロセスに渡らないことを確認（集約処理）
    import subprocess
    import threading

    from src.services import report_launcher

    called = {}

    class DummyPopen:
        def __init__(self, *args, **kwargs):
            called["args"] = args[0]
            called["env"] = kwargs.get("env", {})

        def wait(self):
            return 0

    class DummyThread:
        def __init__(self, *args, **kwargs):
            pass

        def start(self):
            pass  # Don't actually start the thread

    monkeypatch.setattr(subprocess, "Popen", DummyPopen)
    monkeypatch.setattr(threading, "Thread", DummyThread)
    result = report_launcher.execute_aggregation("slug")
    assert "USER_API_KEY" not in called["env"]
    assert called["args"][-2:] == ["--only", "hierarchical_aggregation"]
    assert result is True


def test_launch_report_generation_from_config_uses_shared_command(monkeypatch, tmp_path):
    import subprocess
    import threading

    from src.services import report_launcher

    called = {}
    config_path = tmp_path / "demo.json"
    config_path.write_text("{}", encoding="utf-8")

    class DummyPopen:
        def __init__(self, *args, **kwargs):
            called["args"] = args[0]
            called["env"] = kwargs.get("env", {})

        def wait(self):
            return 0

    class DummyThread:
        def __init__(self, *args, **kwargs):
            pass

        def start(self):
            pass  # Don't actually start the thread

    monkeypatch.setattr(subprocess, "Popen", DummyPopen)
    monkeypatch.setattr(threading, "Thread", DummyThread)

    report_launcher.launch_report_generation_from_config(config_path, "demo")

    assert called["args"][:3] == ["python", "-m", "analysis_core"]
    assert "--without-html" in called["args"]
    assert "--only" not in called["args"]


def test_launch_report_generation_from_config_runs_full_service_flow(monkeypatch, tmp_path):
    import json
    import subprocess
    import threading

    from src.services import report_launcher, report_status

    slug = "demo"
    report_dir = tmp_path / "reports"
    config_dir = tmp_path / "configs"
    input_dir = tmp_path / "inputs"
    data_dir = tmp_path / "data"
    (report_dir / slug).mkdir(parents=True)
    config_dir.mkdir(parents=True)
    input_dir.mkdir(parents=True)
    data_dir.mkdir(parents=True)

    (report_dir / slug / "hierarchical_status.json").write_text(
        json.dumps(
            {
                "status": "completed",
                "completed_jobs": [
                    {"step": "extraction"},
                    {"step": "hierarchical_overview"},
                ],
                "previously_completed_jobs": [
                    {"step": "embedding"},
                ],
                "total_token_usage": 444,
                "token_usage_input": 170,
                "token_usage_output": 274,
            }
        ),
        encoding="utf-8",
    )
    config_path = config_dir / f"{slug}.json"
    config_path.write_text(
        json.dumps(
            {
                "provider": "openai",
                "model": "gpt-4o-mini",
                "question": "Existing title",
                "intro": "Existing description",
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(report_launcher.settings, "REPORT_DIR", report_dir)
    monkeypatch.setattr(report_launcher.settings, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(report_launcher.settings, "INPUT_DIR", input_dir)
    monkeypatch.setattr(report_status.settings, "DATA_DIR", data_dir)
    monkeypatch.setattr(report_status, "STATE_FILE", data_dir / "report_status.json")

    report_status._report_status.clear()
    report_status._report_status[slug] = {
        "slug": slug,
        "source_slug": "origin-slug",
        "status": "processing",
        "title": "Existing title",
        "description": "Existing description",
        "is_pubcom": False,
        "visibility": "unlisted",
        "created_at": "2026-05-20T00:00:00+00:00",
        "token_usage": 10,
        "token_usage_input": 5,
        "token_usage_output": 5,
        "estimated_cost": 0.0,
        "provider": "openai",
        "model": "gpt-4o-mini",
    }
    report_status.save_status()

    calls = {"args": None, "env": None, "syncs": []}

    class DummyPopen:
        def __init__(self, *args, **kwargs):
            calls["args"] = args[0]
            calls["env"] = kwargs.get("env", {})

        def wait(self):
            return 0

    class ImmediateThread:
        def __init__(self, target=None, args=(), kwargs=None, **_):
            self.target = target
            self.args = args
            self.kwargs = kwargs or {}

        def start(self):
            self.target(*self.args, **self.kwargs)

    class DummyReportSyncService:
        def sync_report_files_to_storage(self, value):
            calls["syncs"].append(("report", value))

        def sync_input_file_to_storage(self, value):
            calls["syncs"].append(("input", value))

        def sync_config_file_to_storage(self, value):
            calls["syncs"].append(("config", value))

        def sync_status_file_to_storage(self):
            calls["syncs"].append(("status", None))

    monkeypatch.setattr(subprocess, "Popen", DummyPopen)
    monkeypatch.setattr(threading, "Thread", ImmediateThread)
    monkeypatch.setattr(report_launcher, "ReportSyncService", DummyReportSyncService)

    report_launcher.launch_report_generation_from_config(config_path, slug, user_api_key="test-key")

    updated = report_status._report_status[slug]
    assert calls["env"]["USER_API_KEY"] == "test-key"
    assert calls["args"][:3] == ["python", "-m", "analysis_core"]
    assert "--without-html" in calls["args"]
    assert str(config_path) in calls["args"]
    assert updated["status"] == "ready"
    assert updated["source_slug"] == "origin-slug"
    assert updated["title"] == "Existing title"
    assert updated["description"] == "Existing description"
    assert updated["created_at"] == "2026-05-20T00:00:00+00:00"
    assert updated["token_usage"] == 444
    assert updated["token_usage_input"] == 170
    assert updated["token_usage_output"] == 274
    assert updated["provider"] == "openai"
    assert updated["model"] == "gpt-4o-mini"
    assert calls["syncs"] == [
        ("report", slug),
        ("input", slug),
        ("config", slug),
        ("status", None),
    ]


def test_launch_report_generation_runs_full_service_flow(monkeypatch, tmp_path):
    import json
    import subprocess
    import threading

    from src.schemas.admin_report import Comment, Prompt, ReportInput
    from src.services import report_launcher, report_status

    slug = "demo"
    report_dir = tmp_path / "reports"
    config_dir = tmp_path / "configs"
    input_dir = tmp_path / "inputs"
    data_dir = tmp_path / "data"
    (report_dir / slug).mkdir(parents=True)
    config_dir.mkdir(parents=True)
    input_dir.mkdir(parents=True)
    data_dir.mkdir(parents=True)

    (report_dir / slug / "hierarchical_status.json").write_text(
        json.dumps(
            {
                "status": "completed",
                "completed_jobs": [
                    {"step": "extraction"},
                    {"step": "embedding"},
                ],
                "total_token_usage": 555,
                "token_usage_input": 222,
                "token_usage_output": 333,
            }
        ),
        encoding="utf-8",
    )

    monkeypatch.setattr(report_launcher.settings, "REPORT_DIR", report_dir)
    monkeypatch.setattr(report_launcher.settings, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(report_launcher.settings, "INPUT_DIR", input_dir)
    monkeypatch.setattr(report_status.settings, "DATA_DIR", data_dir)
    monkeypatch.setattr(report_status, "STATE_FILE", data_dir / "report_status.json")

    report_status._report_status.clear()

    calls = {"args": None, "env": None, "syncs": []}

    class DummyPopen:
        def __init__(self, *args, **kwargs):
            calls["args"] = args[0]
            calls["env"] = kwargs.get("env", {})

        def wait(self):
            return 0

    class ImmediateThread:
        def __init__(self, target=None, args=(), kwargs=None, **_):
            self.target = target
            self.args = args
            self.kwargs = kwargs or {}

        def start(self):
            self.target(*self.args, **self.kwargs)

    class DummyReportSyncService:
        def sync_report_files_to_storage(self, value):
            calls["syncs"].append(("report", value))

        def sync_input_file_to_storage(self, value):
            calls["syncs"].append(("input", value))

        def sync_config_file_to_storage(self, value):
            calls["syncs"].append(("config", value))

        def sync_status_file_to_storage(self):
            calls["syncs"].append(("status", None))

    monkeypatch.setattr(subprocess, "Popen", DummyPopen)
    monkeypatch.setattr(threading, "Thread", ImmediateThread)
    monkeypatch.setattr(report_launcher, "ReportSyncService", DummyReportSyncService)

    report_input = ReportInput(
        input=slug,
        question="What changed?",
        intro="Investigate current comments",
        model="gpt-4o-mini",
        provider="openai",
        is_pubcom=False,
        is_embedded_at_local=False,
        local_llm_address=None,
        prompt=Prompt(extraction="ex", initial_labelling="init", merge_labelling="merge", overview="overview"),
        workers=2,
        cluster=[2, 4],
        enable_source_link=True,
        comments=[
            Comment(id="c1", comment="First comment", source="web", url="https://example.com/1"),
            Comment(id="c2", comment="Second comment", source="web", url="https://example.com/2"),
        ],
    )

    report_launcher.launch_report_generation(report_input, user_api_key="test-key")

    config_path = config_dir / f"{slug}.json"
    input_path = input_dir / f"{slug}.csv"
    updated = report_status._report_status[slug]

    assert calls["env"]["USER_API_KEY"] == "test-key"
    assert calls["args"][:3] == ["python", "-m", "analysis_core"]
    assert "--without-html" in calls["args"]
    assert str(config_path) in calls["args"]
    assert config_path.exists()
    assert input_path.exists()
    assert updated["status"] == "ready"
    assert updated["title"] == "What changed?"
    assert updated["description"] == "Investigate current comments"
    assert updated["token_usage"] == 555
    assert updated["token_usage_input"] == 222
    assert updated["token_usage_output"] == 333
    assert updated["provider"] == "openai"
    assert updated["model"] == "gpt-4o-mini"
    assert calls["syncs"] == [
        ("report", slug),
        ("input", slug),
        ("config", slug),
        ("status", None),
    ]


def test_monitor_process_reads_workflow_status_and_syncs_outputs(monkeypatch, tmp_path):
    import json

    from src.services import report_launcher

    slug = "demo"
    report_dir = tmp_path / "reports"
    config_dir = tmp_path / "configs"
    (report_dir / slug).mkdir(parents=True)
    config_dir.mkdir(parents=True)

    (report_dir / slug / "hierarchical_status.json").write_text(
        json.dumps(
            {
                "status": "completed",
                "completed_jobs": [
                    {"step": "extraction"},
                    {"step": "embedding"},
                ],
                "total_token_usage": 321,
                "token_usage_input": 123,
                "token_usage_output": 198,
            }
        ),
        encoding="utf-8",
    )
    (config_dir / f"{slug}.json").write_text(
        json.dumps({"provider": "openai", "model": "gpt-4o-mini"}),
        encoding="utf-8",
    )

    monkeypatch.setattr(report_launcher.settings, "REPORT_DIR", report_dir)
    monkeypatch.setattr(report_launcher.settings, "CONFIG_DIR", config_dir)

    calls = {"statuses": [], "token_usage": None, "syncs": []}

    class DummyProcess:
        def wait(self):
            return 0

    class DummyReportSyncService:
        def sync_report_files_to_storage(self, value):
            calls["syncs"].append(("report", value))

        def sync_input_file_to_storage(self, value):
            calls["syncs"].append(("input", value))

        def sync_config_file_to_storage(self, value):
            calls["syncs"].append(("config", value))

        def sync_status_file_to_storage(self):
            calls["syncs"].append(("status", None))

    monkeypatch.setattr(
        report_launcher, "set_status", lambda current_slug, status: calls["statuses"].append((current_slug, status))
    )
    monkeypatch.setattr(
        report_launcher,
        "update_token_usage",
        lambda *args: calls.__setitem__("token_usage", args),
    )
    monkeypatch.setattr(report_launcher, "ReportSyncService", DummyReportSyncService)

    report_launcher._monitor_process(DummyProcess(), slug)

    assert calls["token_usage"] == (slug, 321, 123, 198, "openai", "gpt-4o-mini")
    assert calls["statuses"] == [(slug, "ready")]
    assert calls["syncs"] == [
        ("report", slug),
        ("input", slug),
        ("config", slug),
        ("status", None),
    ]


def test_monitor_process_preserves_existing_report_status_during_aggregation_rerun(monkeypatch, tmp_path):
    import json

    from src.services import report_launcher, report_status

    slug = "demo"
    report_dir = tmp_path / "reports"
    config_dir = tmp_path / "configs"
    data_dir = tmp_path / "data"
    (report_dir / slug).mkdir(parents=True)
    config_dir.mkdir(parents=True)
    data_dir.mkdir(parents=True)

    (report_dir / slug / "hierarchical_status.json").write_text(
        json.dumps(
            {
                "status": "completed",
                "completed_jobs": [
                    {"step": "extraction"},
                    {"step": "hierarchical_aggregation"},
                ],
                "previously_completed_jobs": [
                    {"step": "embedding"},
                ],
                "total_token_usage": 654,
                "token_usage_input": 210,
                "token_usage_output": 444,
            }
        ),
        encoding="utf-8",
    )
    (config_dir / f"{slug}.json").write_text(
        json.dumps({"provider": "openai", "model": "gpt-4o-mini"}),
        encoding="utf-8",
    )

    monkeypatch.setattr(report_launcher.settings, "REPORT_DIR", report_dir)
    monkeypatch.setattr(report_launcher.settings, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(report_status.settings, "DATA_DIR", data_dir)
    monkeypatch.setattr(report_status, "STATE_FILE", data_dir / "report_status.json")

    report_status._report_status.clear()
    report_status._report_status[slug] = {
        "slug": slug,
        "source_slug": None,
        "status": "processing",
        "title": "Existing title",
        "description": "Existing description",
        "is_pubcom": False,
        "visibility": "unlisted",
        "created_at": "2026-05-20T00:00:00+00:00",
        "token_usage": 111,
        "token_usage_input": 11,
        "token_usage_output": 100,
        "estimated_cost": 0.0,
        "provider": "openai",
        "model": "gpt-4o-mini",
    }
    report_status.save_status()

    syncs = []

    class DummyProcess:
        def wait(self):
            return 0

    class DummyReportSyncService:
        def sync_report_files_to_storage(self, value):
            syncs.append(("report", value))

        def sync_input_file_to_storage(self, value):
            syncs.append(("input", value))

        def sync_config_file_to_storage(self, value):
            syncs.append(("config", value))

        def sync_status_file_to_storage(self):
            syncs.append(("status", None))

    monkeypatch.setattr(report_launcher, "ReportSyncService", DummyReportSyncService)

    report_launcher._monitor_process(DummyProcess(), slug)

    updated = report_status._report_status[slug]
    assert updated["status"] == "ready"
    assert updated["title"] == "Existing title"
    assert updated["description"] == "Existing description"
    assert updated["created_at"] == "2026-05-20T00:00:00+00:00"
    assert updated["token_usage"] == 654
    assert updated["token_usage_input"] == 210
    assert updated["token_usage_output"] == 444
    assert updated["provider"] == "openai"
    assert updated["model"] == "gpt-4o-mini"
    assert syncs == [
        ("report", slug),
        ("input", slug),
        ("config", slug),
        ("status", None),
    ]


def test_monitor_process_persists_error_log_excerpt_when_process_fails(monkeypatch, tmp_path):
    import json

    from src.services import report_launcher

    slug = "demo"
    report_dir = tmp_path / "reports"
    config_dir = tmp_path / "configs"
    (report_dir / slug).mkdir(parents=True)
    config_dir.mkdir(parents=True)

    log_path = report_dir / slug / report_launcher.ANALYSIS_LOG_FILENAME
    log_path.write_text("line 1\nline 2\nRuntimeError: boom", encoding="utf-8")

    monkeypatch.setattr(report_launcher.settings, "REPORT_DIR", report_dir)
    monkeypatch.setattr(report_launcher.settings, "CONFIG_DIR", config_dir)

    calls = {"statuses": []}

    class DummyProcess:
        def wait(self):
            return 1

    monkeypatch.setattr(
        report_launcher, "set_status", lambda current_slug, status: calls["statuses"].append((current_slug, status))
    )

    report_launcher._monitor_process(DummyProcess(), slug)

    status_data = json.loads((report_dir / slug / "hierarchical_status.json").read_text(encoding="utf-8"))
    assert status_data["status"] == "error"
    assert status_data["current_job"] == "error"
    assert status_data["error"] == "analysis-core exited with a non-zero status; see error_log_excerpt"
    assert status_data["error_log_path"] == report_launcher.ANALYSIS_LOG_FILENAME
    assert status_data["error_log_excerpt"] == "line 1\nline 2\nRuntimeError: boom"
    assert calls["statuses"] == [(slug, "error")]


def test_execute_aggregation_runs_monitor_flow_and_preserves_existing_status(monkeypatch, tmp_path):
    import json
    import subprocess
    import threading

    from src.services import report_launcher, report_status

    slug = "demo"
    report_dir = tmp_path / "reports"
    config_dir = tmp_path / "configs"
    input_dir = tmp_path / "inputs"
    data_dir = tmp_path / "data"
    (report_dir / slug).mkdir(parents=True)
    config_dir.mkdir(parents=True)
    input_dir.mkdir(parents=True)
    data_dir.mkdir(parents=True)

    (report_dir / slug / "hierarchical_status.json").write_text(
        json.dumps(
            {
                "status": "completed",
                "completed_jobs": [
                    {"step": "hierarchical_aggregation"},
                ],
                "total_token_usage": 777,
                "token_usage_input": 300,
                "token_usage_output": 477,
            }
        ),
        encoding="utf-8",
    )
    config_path = config_dir / f"{slug}.json"
    config_path.write_text(
        json.dumps({"provider": "openai", "model": "gpt-4o-mini"}),
        encoding="utf-8",
    )

    monkeypatch.setattr(report_launcher.settings, "REPORT_DIR", report_dir)
    monkeypatch.setattr(report_launcher.settings, "CONFIG_DIR", config_dir)
    monkeypatch.setattr(report_launcher.settings, "INPUT_DIR", input_dir)
    monkeypatch.setattr(report_status.settings, "DATA_DIR", data_dir)
    monkeypatch.setattr(report_status, "STATE_FILE", data_dir / "report_status.json")

    report_status._report_status.clear()
    report_status._report_status[slug] = {
        "slug": slug,
        "source_slug": None,
        "status": "processing",
        "title": "Existing title",
        "description": "Existing description",
        "is_pubcom": False,
        "visibility": "unlisted",
        "created_at": "2026-05-20T00:00:00+00:00",
        "token_usage": 1,
        "token_usage_input": 1,
        "token_usage_output": 0,
        "estimated_cost": 0.0,
        "provider": "openai",
        "model": "gpt-4o-mini",
    }
    report_status.save_status()

    calls = {"args": None, "env": None, "syncs": []}

    class DummyPopen:
        def __init__(self, *args, **kwargs):
            calls["args"] = args[0]
            calls["env"] = kwargs.get("env", {})

        def wait(self):
            return 0

    class ImmediateThread:
        def __init__(self, target=None, args=(), kwargs=None, **_):
            self.target = target
            self.args = args
            self.kwargs = kwargs or {}

        def start(self):
            self.target(*self.args, **self.kwargs)

    class DummyReportSyncService:
        def sync_report_files_to_storage(self, value):
            calls["syncs"].append(("report", value))

        def sync_input_file_to_storage(self, value):
            calls["syncs"].append(("input", value))

        def sync_config_file_to_storage(self, value):
            calls["syncs"].append(("config", value))

        def sync_status_file_to_storage(self):
            calls["syncs"].append(("status", None))

    monkeypatch.setattr(subprocess, "Popen", DummyPopen)
    monkeypatch.setattr(threading, "Thread", ImmediateThread)
    monkeypatch.setattr(report_launcher, "ReportSyncService", DummyReportSyncService)

    result = report_launcher.execute_aggregation(slug, user_api_key="test-key")

    updated = report_status._report_status[slug]
    assert result is True
    assert calls["env"]["USER_API_KEY"] == "test-key"
    assert calls["args"][:3] == ["python", "-m", "analysis_core"]
    assert calls["args"][-2:] == ["--only", "hierarchical_aggregation"]
    assert str(config_path) in calls["args"]
    assert updated["status"] == "ready"
    assert updated["title"] == "Existing title"
    assert updated["description"] == "Existing description"
    assert updated["token_usage"] == 777
    assert updated["token_usage_input"] == 300
    assert updated["token_usage_output"] == 477
    assert calls["syncs"] == [
        ("report", slug),
        ("input", slug),
        ("config", slug),
        ("status", None),
    ]
