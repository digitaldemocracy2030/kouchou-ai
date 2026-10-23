"""extraction.limit で回答を切り詰めたときは、黙らずに件数を警告する。"""

import importlib
import logging

import pytest

extraction = importlib.import_module("analysis_core.steps.extraction")


def _run(tmp_path, monkeypatch, n_comments: int, limit: int):
    inputs = tmp_path / "inputs"
    (tmp_path / "outputs" / "report").mkdir(parents=True)
    inputs.mkdir()
    rows = "".join(f"c{i},意見{i}\n" for i in range(n_comments))
    # 空の回答は除外される（#583）ので、切り詰めの判定には数えない
    (inputs / "input.csv").write_text("comment-id,comment-body\n" + rows + "empty,\n", encoding="utf-8")
    config = {
        "input": "input",
        "output_dir": "report",
        "provider": "openai",
        "_input_base_dir": str(inputs),
        "_output_base_dir": str(tmp_path / "outputs"),
        "extraction": {"model": "m", "prompt": "p", "workers": 2, "limit": limit, "properties": []},
    }
    monkeypatch.setattr(extraction, "update_progress", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        extraction, "request_to_chat_ai", lambda **kwargs: ('{"extractedOpinionList": ["意見"]}', 1, 1, 2)
    )
    extraction.extraction(config)


def test_warns_when_limit_truncates_comments(tmp_path, monkeypatch, caplog):
    with caplog.at_level(logging.WARNING):
        _run(tmp_path, monkeypatch, n_comments=5, limit=3)

    warnings = [r.getMessage() for r in caplog.records if r.levelno >= logging.WARNING]
    assert len(warnings) == 1
    assert "5件" in warnings[0]
    assert "3件" in warnings[0]
    assert "残りの 2件" in warnings[0]
    assert "extraction.limit=3" in warnings[0]


@pytest.mark.parametrize("limit", [5, 1000])
def test_no_warning_when_all_comments_are_processed(tmp_path, monkeypatch, caplog, limit):
    with caplog.at_level(logging.WARNING):
        _run(tmp_path, monkeypatch, n_comments=5, limit=limit)

    assert [r for r in caplog.records if r.levelno >= logging.WARNING] == []
