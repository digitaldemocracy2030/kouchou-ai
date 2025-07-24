def test_user_api_key_propagation_to_env(monkeypatch):
    # user_api_keyが指定された場合、その値が環境変数USER_API_KEYにセットされてサブプロセスに渡ることを確認
    import subprocess

    from src.schemas.admin_report import Prompt, ReportInput
    from src.services import report_launcher

    called = {}

    class DummyPopen:
        def __init__(self, *args, **kwargs):
            called["env"] = kwargs.get("env", {})

        def wait(self):
            return 0

    monkeypatch.setattr(subprocess, "Popen", DummyPopen)
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


def test_env_user_api_key_not_set_when_user_api_key_not_provided(monkeypatch):
    # user_api_keyが指定されない場合、USER_API_KEYが環境変数にセットされずサブプロセスに渡らないことを確認
    import subprocess

    from src.schemas.admin_report import Prompt, ReportInput
    from src.services import report_launcher

    called = {}

    class DummyPopen:
        def __init__(self, *args, **kwargs):
            called["env"] = kwargs.get("env", {})

        def wait(self):
            return 0

    monkeypatch.setattr(subprocess, "Popen", DummyPopen)
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


def test_env_user_api_key_not_set_when_user_api_key_empty(monkeypatch):
    # user_api_keyが空文字列の場合、USER_API_KEYが環境変数にセットされずサブプロセスに渡らないことを確認
    import subprocess

    from src.schemas.admin_report import Prompt, ReportInput
    from src.services import report_launcher

    called = {}

    class DummyPopen:
        def __init__(self, *args, **kwargs):
            called["env"] = kwargs.get("env", {})

        def wait(self):
            return 0

    monkeypatch.setattr(subprocess, "Popen", DummyPopen)
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


def test_user_api_key_propagation_to_env_in_aggregation(monkeypatch):
    # user_api_keyが指定された場合、その値が環境変数USER_API_KEYにセットされてサブプロセスに渡ることを確認（集約処理）
    import subprocess

    from src.services import report_launcher

    called = {}

    class DummyPopen:
        def __init__(self, *args, **kwargs):
            called["env"] = kwargs.get("env", {})

        def wait(self):
            return 0

    monkeypatch.setattr(subprocess, "Popen", DummyPopen)
    result = report_launcher.execute_aggregation("slug", user_api_key="test-key")
    assert called["env"]["USER_API_KEY"] == "test-key"
    assert result is True


def test_env_user_api_key_not_set_in_aggregation_when_user_api_key_not_provided(monkeypatch):
    # user_api_keyが指定されない場合、USER_API_KEYが環境変数にセットされずサブプロセスに渡らないことを確認（集約処理）
    import subprocess

    from src.services import report_launcher

    called = {}

    class DummyPopen:
        def __init__(self, *args, **kwargs):
            called["env"] = kwargs.get("env", {})

        def wait(self):
            return 0

    monkeypatch.setattr(subprocess, "Popen", DummyPopen)
    result = report_launcher.execute_aggregation("slug")
    assert "USER_API_KEY" not in called["env"]
    assert result is True
