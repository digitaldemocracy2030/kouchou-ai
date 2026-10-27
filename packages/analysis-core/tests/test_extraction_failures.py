"""A failed extraction must not silently remove an input from the analysis (#905)."""

import importlib
import json
import time

import pytest

extraction = importlib.import_module("analysis_core.steps.extraction")


def test_batch_keeps_order_and_legitimate_empty_response(monkeypatch):
    monkeypatch.setattr(extraction, "extract_arguments", lambda text, *args: ([text] if text else [], 2, 1, 3))
    config = {}
    assert extraction.extract_batch(["first", "", "last"], "prompt", "model", 3, config=config) == [
        ["first"],
        [],
        ["last"],
    ]
    assert config["total_token_usage"] == 9


def test_batch_failure_counts_and_retains_successful_usage(monkeypatch):
    def extract(text, *args):
        if text == "private input":
            raise RuntimeError("private API error")
        return [text], 2, 1, 3

    monkeypatch.setattr(extraction, "extract_arguments", extract)
    config = {"total_token_usage": 10, "token_usage_input": 7, "token_usage_output": 3}
    with pytest.raises(extraction.ExtractionBatchError, match="1件") as error:
        extraction.extract_batch(["good", "private input"], "p", "m", 2, config=config, comment_ids=["c1", "c2"])
    assert error.value.failures == {1: "RuntimeError"}
    assert "c2" in str(error.value)
    assert "private" not in str(error.value)
    assert config == {"total_token_usage": 13, "token_usage_input": 9, "token_usage_output": 4}


def test_slow_success_beyond_request_timeout_is_not_reported_as_timeout(monkeypatch):
    """Flex や SDK 内部リトライで timeout_seconds を超えて成功した応答を捨てない。

    1 リクエストの上限は各プロバイダの SDK に渡す timeout が担う。バッチ側で同じ値の
    待機上限を重ねると、遅れて成功した応答まで TimeoutError として分析を中断していた。
    """

    def extract(text, *args):
        if text == "slow":
            time.sleep(0.3)
        return [text], 2, 1, 3

    monkeypatch.setattr(extraction, "extract_arguments", extract)
    config = {}
    assert extraction.extract_batch(["fast", "slow"], "p", "m", 2, config=config, timeout_seconds=0.05) == [
        ["fast"],
        ["slow"],
    ]
    # 遅れて完了した応答のトークンも集計する
    assert config["total_token_usage"] == 6


@pytest.mark.parametrize("response", ["broken JSON", "{}", '{"extractedOpinionList": null}'])
def test_malformed_llm_response_fails_batch(monkeypatch, response):
    monkeypatch.setattr(extraction, "request_to_chat_ai", lambda **kwargs: (response, 2, 1, 3))
    with pytest.raises(extraction.ExtractionBatchError) as error:
        extraction.extract_batch(["private input"], "p", "m", 1)
    assert error.value.failures == {0: "ValueError"}


@pytest.mark.parametrize("execution", ["legacy", "workflow"])
def test_extraction_failure_does_not_publish_partial_outputs(tmp_path, monkeypatch, execution):
    from analysis_core.core.orchestration import run_step, termination

    inputs = tmp_path / "inputs"
    outputs = tmp_path / "outputs"
    inputs.mkdir()
    report = outputs / "report"
    report.mkdir(parents=True)
    (inputs / "input.csv").write_text("comment-id,comment-body\nc1,good\nc2,bad\n")
    config = {
        "input": "input",
        "output_dir": "report",
        "provider": "openai",
        "_input_base_dir": str(inputs),
        "_output_base_dir": str(outputs),
        "extraction": {"model": "m", "prompt": "p", "workers": 1, "limit": 2, "properties": []},
        "plan": [{"step": "extraction", "run": True}],
    }

    def request(**kwargs):
        if kwargs["messages"][-1]["content"] == "bad":
            raise RuntimeError("private error")
        return '{"extractedOpinionList": ["opinion"]}', 2, 1, 3

    monkeypatch.setattr(extraction, "request_to_chat_ai", request)
    if execution == "legacy":
        with pytest.raises(extraction.ExtractionBatchError):
            try:
                run_step("extraction", extraction.extraction, config)
            except extraction.ExtractionBatchError as error:
                termination(config, error)
    else:
        from analysis_core.orchestrator import PipelineOrchestrator

        result = PipelineOrchestrator(config).run_default()
        assert not result.success
        assert [step.step_name for step in result.steps] == ["extraction"]
    status = json.loads((report / "hierarchical_status.json").read_text())
    assert status["status"] == "error"
    assert "c2" in status["error"]
    assert "private error" not in status["error"]
    assert status.get("completed_jobs", []) == []
    if execution == "legacy":
        assert status["total_token_usage"] == 3
    assert not (report / "args.csv").exists()
    assert not (report / "relations.csv").exists()


def test_diagnostics_distinguish_empty_and_error_without_raw_exception(tmp_path, monkeypatch):
    def extract(text, *args):
        if text == "失敗した原文":
            raise ValueError("secret API response")
        return ([text] if text == "成功" else []), 0, 0, 0

    monkeypatch.setattr(extraction, "extract_arguments", extract)
    path = tmp_path / "diagnostics.jsonl"
    with pytest.raises(extraction.ExtractionBatchError):
        extraction.extract_batch(
            ["成功", "意見なし", "失敗した原文"], "p", "m", 3,
            comment_ids=["a", "b", "c"], diagnostics_path=path,
        )
    records = [json.loads(line) for line in path.read_text().splitlines()]
    assert records == [
        {"comment_id": "b", "comment": "意見なし", "status": "empty", "error_type": None},
        {"comment_id": "c", "comment": "失敗した原文", "status": "error", "error_type": "ValueError"},
    ]
    assert "secret" not in path.read_text()


def test_content_filter_block_excludes_only_that_comment(tmp_path, monkeypatch, caplog):
    """コンテンツフィルタは回答ごとに決まる拒否なので、1 件で分析全体を止めずにその回答だけ除外する。"""
    from analysis_core.services.llm import LLMSafetyBlockError

    def extract(text, *args):
        if text == "止められた原文":
            raise LLMSafetyBlockError("Azure OpenAI: the prompt was blocked by the content filter (hate)")
        return [text], 2, 1, 3

    monkeypatch.setattr(extraction, "extract_arguments", extract)
    path = tmp_path / "diagnostics.jsonl"
    config = {"extraction_blocked_comment_ids": ["前回の残り"]}
    with caplog.at_level("WARNING"):
        results = extraction.extract_batch(
            ["first", "止められた原文", "last"], "p", "m", 3,
            config=config, comment_ids=["a", "b", "c"], diagnostics_path=path,
        )
    assert results == [["first"], [], ["last"]]
    assert config["extraction_blocked_comment_ids"] == ["b"]
    assert config["total_token_usage"] == 6
    assert [json.loads(line) for line in path.read_text().splitlines()] == [
        {"comment_id": "b", "comment": "止められた原文", "status": "blocked", "error_type": "LLMSafetyBlockError"},
    ]
    # 除外したことは警告ログに残す（原文は出さない）
    assert "1件の回答を分析から除外しました" in caplog.text
    assert "止められた原文" not in caplog.text


def test_no_block_clears_previous_blocked_ids(monkeypatch):
    monkeypatch.setattr(extraction, "extract_arguments", lambda text, *args: ([text], 0, 0, 0))
    config = {"extraction_blocked_comment_ids": ["前回の残り"]}
    extraction.extract_batch(["x"], "p", "m", 1, config=config, comment_ids=["a"])
    assert "extraction_blocked_comment_ids" not in config


def test_other_failures_still_stop_even_with_blocked_comments(monkeypatch):
    from analysis_core.services.llm import LLMSafetyBlockError

    def extract(text, *args):
        if text == "blocked":
            raise LLMSafetyBlockError("blocked")
        raise RuntimeError("private API error")

    monkeypatch.setattr(extraction, "extract_arguments", extract)
    config = {"extraction_blocked_comment_ids": ["前回の残り"]}
    with pytest.raises(extraction.ExtractionBatchError) as error:
        extraction.extract_batch(["blocked", "broken"], "p", "m", 1, config=config, comment_ids=["c1", "c2"])
    assert error.value.failures == {1: "RuntimeError"}
    # 中断するときも、今回の除外を記録する（前回の値は残さない）
    assert config["extraction_blocked_comment_ids"] == ["c1"]


def test_batch_error_message_explains_known_failure_types():
    message = str(extraction.ExtractionBatchError({0: "AuthenticationError", 1: "BadRequestError"}, ["c1", "c2"]))
    assert "理由: AuthenticationError（API キーが無効です）、BadRequestError（" in message
    assert "c1" in message and "c2" in message
    assert "分析ログ" in message
    # 説明の無い型名はそのまま出す
    assert "理由: RuntimeError。" in str(extraction.ExtractionBatchError({0: "RuntimeError"}))


def test_all_comments_blocked_fails_with_content_filter_message(tmp_path, monkeypatch):
    from analysis_core.services.llm import LLMSafetyBlockError

    inputs = tmp_path / "inputs"
    outputs = tmp_path / "outputs"
    inputs.mkdir()
    (outputs / "report").mkdir(parents=True)
    (inputs / "input.csv").write_text("comment-id,comment-body\nc1,bad\n")
    config = {
        "input": "input",
        "output_dir": "report",
        "provider": "azure",
        "_input_base_dir": str(inputs),
        "_output_base_dir": str(outputs),
        "extraction": {"model": "m", "prompt": "p", "workers": 1, "limit": 1, "properties": []},
    }

    def request(**kwargs):
        raise LLMSafetyBlockError("blocked")

    monkeypatch.setattr(extraction, "request_to_chat_ai", request)
    with pytest.raises(RuntimeError, match="コンテンツフィルタに止められた回答が1件"):
        extraction.extraction(config)


def test_partly_blocked_and_rest_empty_is_not_blamed_on_the_filter(tmp_path, monkeypatch):
    """止められなかった回答も意見 0 件なら、フィルタのせいとは言わず通常の空の結果として扱う。"""
    from analysis_core.services.llm import LLMSafetyBlockError

    inputs = tmp_path / "inputs"
    outputs = tmp_path / "outputs"
    inputs.mkdir()
    (outputs / "report").mkdir(parents=True)
    (inputs / "input.csv").write_text("comment-id,comment-body\nc1,bad\nc2,nothing\n")
    config = {
        "input": "input",
        "output_dir": "report",
        "provider": "azure",
        "_input_base_dir": str(inputs),
        "_output_base_dir": str(outputs),
        "extraction": {"model": "m", "prompt": "p", "workers": 1, "limit": 2, "properties": []},
    }

    def request(**kwargs):
        if kwargs["messages"][-1]["content"] == "bad":
            raise LLMSafetyBlockError("blocked")
        return '{"extractedOpinionList": []}', 2, 1, 3

    monkeypatch.setattr(extraction, "request_to_chat_ai", request)
    with pytest.raises(RuntimeError, match="result is empty"):
        extraction.extraction(config)
