"""hierarchical_overview must publish only the summary text, never raw JSON."""

import importlib

import pytest

overview = importlib.import_module("analysis_core.steps.hierarchical_overview")


def _run(tmp_path, monkeypatch, response):
    report = tmp_path / "report"
    report.mkdir()
    (report / "hierarchical_merge_labels.csv").write_text(
        "level,id,label,description\n1,1_0,ラベル,説明\n", encoding="utf-8"
    )
    monkeypatch.setattr(overview, "request_to_chat_ai", lambda **kwargs: (response, 1, 1, 2))
    config = {
        "output_dir": "report",
        "_output_base_dir": str(tmp_path),
        "provider": "local",
        "hierarchical_overview": {"prompt": "p", "model": "m"},
    }
    overview.hierarchical_overview(config)
    return (report / "hierarchical_overview.txt").read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "response",
    [
        {"summary": "全体の要約"},
        '{"summary": "全体の要約"}',
        '<think>考え中 {"x": 1}</think>\n{"summary": "全体の要約"}',
        '<think>考え中</think>\n```json\n{"summary": "全体の要約"}\n```',
        '要約を出力します。\n{"summary": "全体の要約"}',
    ],
)
def test_summary_is_extracted(tmp_path, monkeypatch, response):
    assert _run(tmp_path, monkeypatch, response) == "全体の要約"


@pytest.mark.parametrize(
    "response",
    [
        '<think>考え中</think>\n{"summary": "途中で切れ',
        '{"overview": "summary キーがない"}',
        "<think>考えただけ</think>",
        None,
    ],
)
def test_unusable_response_fails_without_publishing(tmp_path, monkeypatch, response):
    with pytest.raises(RuntimeError, match="overview"):
        _run(tmp_path, monkeypatch, response)
    assert not (tmp_path / "report" / "hierarchical_overview.txt").exists()


def test_plain_text_summary_after_think_is_kept(tmp_path, monkeypatch):
    """JSON を返さず要約文だけを返すローカルモデルの従来動作は維持する。"""
    assert _run(tmp_path, monkeypatch, "<think>考え中</think>\n全体の要約です。") == "全体の要約です。"
