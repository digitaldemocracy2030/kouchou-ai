"""複製元の入力 CSV を取得できず、抽出済みの意見から入力を作り直したことを黙らないことの回帰テスト（x012）。

作り直した入力では、意見がもう一度抽出され、属性フィルタが消え、件数が回答数ではなく意見数になる。
旧形式レポートの救済として作り直し自体は続けるが、ログと status に警告を残して利用者に分かるようにする。
"""

import json
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

SOURCE_SLUG = "source"
NEW_SLUG = "copy"


@pytest.fixture
def env(monkeypatch, tmp_path):
    from src.services import report_duplicate, report_status

    env = SimpleNamespace(
        reports=tmp_path / "reports",
        configs=tmp_path / "configs",
        inputs=tmp_path / "inputs",
        state_file=tmp_path / "report_status.json",
        launched=[],
    )
    for path in (env.reports / SOURCE_SLUG, env.configs, env.inputs):
        path.mkdir(parents=True)
    monkeypatch.setattr(report_duplicate.settings, "REPORT_DIR", env.reports)
    monkeypatch.setattr(report_duplicate.settings, "CONFIG_DIR", env.configs)
    monkeypatch.setattr(report_duplicate.settings, "INPUT_DIR", env.inputs)
    monkeypatch.setattr(report_status, "STATE_FILE", env.state_file)
    monkeypatch.setattr(report_status, "_report_status", {})
    # ストレージは何も取得しない（local 運用と同じ。Azure で取得に失敗した場合も同じ経路に入る）
    monkeypatch.setattr(report_duplicate, "ReportSyncService", MagicMock())
    monkeypatch.setattr(
        report_duplicate,
        "launch_report_generation_from_config",
        lambda config_path, slug, user_api_key=None: env.launched.append(slug),
    )
    env.logger = MagicMock()
    monkeypatch.setattr(report_duplicate, "logger", env.logger)

    config = {
        "name": SOURCE_SLUG,
        "input": SOURCE_SLUG,
        "question": "Q",
        "intro": "I",
        "provider": "openai",
        "model": "gpt-4o-mini",
        "extraction": {"workers": 1, "prompt": "ex", "limit": 2},
        "hierarchical_clustering": {"cluster_nums": [2, 4]},
    }
    (env.configs / f"{SOURCE_SLUG}.json").write_text(json.dumps(config), encoding="utf-8")
    arguments = [
        {"arg_id": "A1_0", "argument": "意見1", "attributes": {"地域": "東"}},
        {"arg_id": "A1_1", "argument": "意見2", "attributes": {"地域": "東"}},
        {"arg_id": "A2_0", "argument": "意見3", "attributes": {"地域": "西"}},
    ]
    (env.reports / SOURCE_SLUG / "hierarchical_result.json").write_text(
        json.dumps({"arguments": arguments}), encoding="utf-8"
    )
    return env


def _duplicate():
    from src.schemas.admin_report import ReportDuplicateRequest, ReportDuplicateReuse
    from src.services import report_duplicate

    return report_duplicate.duplicate_report(
        SOURCE_SLUG, ReportDuplicateRequest(new_slug=NEW_SLUG, reuse=ReportDuplicateReuse(enabled=True))
    )


def _new_report():
    from src.services.report_status import load_status_as_reports

    return next(report for report in load_status_as_reports() if report.slug == NEW_SLUG)


def test_rebuilt_input_is_recorded_as_warning_in_status_and_log(env):
    from src.services import report_duplicate

    assert _duplicate() == NEW_SLUG

    # 旧形式レポートの救済として、作り直した入力で複製は続ける
    assert env.launched == [NEW_SLUG]
    assert (env.inputs / f"{NEW_SLUG}.csv").read_text(encoding="utf-8").count("reuse-argument") == 3

    stored = json.loads(env.state_file.read_text(encoding="utf-8"))[NEW_SLUG]
    assert stored["warnings"] == [report_duplicate.SOURCE_INPUT_RECONSTRUCTED_WARNING]
    # 管理 API のレポート一覧（Report）からも読める
    assert _new_report().warnings == [report_duplicate.SOURCE_INPUT_RECONSTRUCTED_WARNING]

    env.logger.warning.assert_called()
    message = " ".join(str(arg) for call in env.logger.warning.call_args_list for arg in call.args)
    assert SOURCE_SLUG in message and "作り直" in message


def test_copied_input_has_no_warning(env):
    (env.inputs / f"{SOURCE_SLUG}.csv").write_text("comment-id,comment-body\n1,hello\n2,world\n", encoding="utf-8")

    _duplicate()

    stored = json.loads(env.state_file.read_text(encoding="utf-8"))[NEW_SLUG]
    assert "warnings" not in stored
    assert _new_report().warnings is None
    messages = " ".join(str(arg) for call in env.logger.warning.call_args_list for arg in call.args)
    assert "作り直" not in messages
