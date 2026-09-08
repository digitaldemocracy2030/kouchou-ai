"""A failed extraction must not silently remove an input from the analysis (#905)."""

import concurrent.futures
import importlib
import json

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


def test_unfinished_future_is_reported_as_timeout(monkeypatch):
    completed = concurrent.futures.Future()
    completed.set_result((["done"], 2, 1, 3))
    unfinished = concurrent.futures.Future()

    class Executor:
        def __init__(self, **kwargs):
            self.futures = iter([completed, unfinished])

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def submit(self, *args):
            return next(self.futures)

    monkeypatch.setattr(extraction.concurrent.futures, "ThreadPoolExecutor", Executor)
    with pytest.raises(extraction.ExtractionBatchError) as error:
        extraction.extract_batch(["one", "two"], "p", "m", 2, timeout_seconds=0)
    assert error.value.failures == {1: "TimeoutError"}
    assert unfinished.cancelled()


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
