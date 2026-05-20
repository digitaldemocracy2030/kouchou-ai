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

    monkeypatch.setattr(report_launcher, "set_status", lambda current_slug, status: calls["statuses"].append((current_slug, status)))
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
