"""Label failures must stop both pipeline execution paths (#915)."""

import importlib
import json

import polars as pl
import pytest

from analysis_core.steps._labelling import LabellingBatchError

initial = importlib.import_module("analysis_core.steps.hierarchical_initial_labelling")
merge = importlib.import_module("analysis_core.steps.hierarchical_merge_labelling")


def clusters():
    return pl.DataFrame(
        {
            "argument": ["private one", "private two", "private three", "private four"],
            "cluster-level-1-id": ["p1", "p1", "p2", "p2"],
            "cluster-level-2-id": ["c1", "c2", "c3", "c4"],
            "cluster-level-2-label": ["one", "two", "three", "four"],
            "cluster-level-2-description": ["description"] * 4,
        }
    )


def run_batch(stage, config):
    df = clusters()
    if stage == "initial":
        return initial.initial_labelling(
            "prompt", df.drop("cluster-level-2-label", "cluster-level-2-description"), 1, "m", 4, config=config
        )
    return merge.merge_labelling(df, ["cluster-level-2-id", "cluster-level-1-id"], config)


@pytest.mark.parametrize("stage", ["initial", "merge"])
@pytest.mark.parametrize(
    "response,kind",
    [
        (RuntimeError("private API failure"), "RuntimeError"),
        (TimeoutError("private timeout"), "timeout"),
        ("broken JSON", "invalid_response"),
        ({"label": "only"}, "invalid_response"),
        ({"label": " ", "description": "text"}, "invalid_response"),
        ({"label": 5, "description": "text"}, "invalid_response"),
        ([], "invalid_response"),
    ],
)
def test_failure_reports_stage_count_and_ids(monkeypatch, stage, response, kind):
    def request(**kwargs):
        if isinstance(response, Exception):
            raise response
        return response, 2, 1, 3

    monkeypatch.setattr(initial if stage == "initial" else merge, "request_to_chat_ai", request)
    config = {
        "provider": "openai",
        "hierarchical_merge_labelling": {"sampling_num": 1, "prompt": "p", "model": "m", "workers": 2},
    }
    with pytest.raises(LabellingBatchError) as error:
        run_batch(stage, config)
    expected = ["c1", "c2", "c3", "c4"] if stage == "initial" else ["p1", "p2"]
    assert error.value.failures == dict.fromkeys(expected, kind)
    assert f"hierarchical_{stage}_labelling" in str(error.value)
    assert f"{len(expected)}件" in str(error.value)
    assert "private" not in str(error.value)


@pytest.mark.parametrize("stage", ["initial", "merge"])
def test_success_and_concurrent_usage(monkeypatch, stage):
    monkeypatch.setattr(
        initial if stage == "initial" else merge,
        "request_to_chat_ai",
        lambda **kwargs: ('{"label":"label","description":"description"}', 2, 1, 3),
    )
    config = {
        "provider": "openai",
        "hierarchical_merge_labelling": {"sampling_num": 1, "prompt": "p", "model": "m", "workers": 2},
    }
    result = run_batch(stage, config)
    assert len(result) == 4
    assert config["total_token_usage"] == (12 if stage == "initial" else 6)
    assert config["token_usage_input"] == (8 if stage == "initial" else 4)
    assert config["token_usage_output"] == (4 if stage == "initial" else 2)


@pytest.mark.parametrize("stage", ["initial", "merge"])
@pytest.mark.parametrize("execution", ["legacy", "workflow"])
def test_failed_step_stops_before_downstream_and_output(tmp_path, monkeypatch, stage, execution):
    from analysis_core.core.orchestration import run_step, termination
    from analysis_core.orchestrator import PipelineOrchestrator

    report = tmp_path / "report"
    report.mkdir()
    clusters().drop("cluster-level-2-label", "cluster-level-2-description").write_csv(
        report / "hierarchical_clusters.csv"
    )
    if stage == "merge":
        clusters().write_csv(report / "hierarchical_initial_labels.csv")
    step = f"hierarchical_{stage}_labelling"
    config = {
        "output_dir": "report",
        "_output_base_dir": str(tmp_path),
        "provider": "openai",
        "model": "m",
        "estimated_cost": 12.5,
        step: {"model": "m", "prompt": "p", "sampling_num": 1, "workers": 2},
        "plan": [
            {"step": name, "run": False}
            for name in ["extraction", "embedding", "hierarchical_clustering"]
            + (["hierarchical_initial_labelling"] if stage == "merge" else [])
        ]
        + [{"step": step, "run": True}],
    }

    def request(**kwargs):
        raise RuntimeError("private API failure")

    module = initial if stage == "initial" else merge
    monkeypatch.setattr(module, "request_to_chat_ai", request)
    if execution == "legacy":
        with pytest.raises(LabellingBatchError):
            try:
                run_step(step, getattr(module, step), config)
            except LabellingBatchError as error:
                termination(config, error)
    else:
        result = PipelineOrchestrator(config).run_default()
        assert not result.success
        if stage == "initial":
            assert not any(s.step_name in ("merge_labelling", "hierarchical_merge_labelling") for s in result.steps)
        assert not any(
            s.step_name
            in ("overview", "aggregation", "visualization", "hierarchical_overview", "hierarchical_aggregation")
            for s in result.steps
        )
    status = json.loads((report / "hierarchical_status.json").read_text())
    assert status["status"] == "error"
    assert step in status["error"]
    assert "private" not in status["error"]
    assert status["token_usage_complete"] is False
    assert status["estimated_cost"] is None
    assert not (report / f"hierarchical_{stage}_labels.csv").exists()
    assert not (report / "hierarchical_result.json").exists()


def test_successful_and_malformed_response_usage_is_retained(monkeypatch):
    def request(**kwargs):
        text = kwargs["messages"][-1]["content"]
        if text == "private one":
            raise RuntimeError("private API failure")
        if text == "private two":
            return "broken JSON", 2, 1, 3
        return {"label": "valid", "description": "valid"}, 2, 1, 3

    monkeypatch.setattr(initial, "request_to_chat_ai", request)
    config = {}
    with pytest.raises(LabellingBatchError) as error:
        run_batch("initial", config)
    assert error.value.failures == {"c1": "RuntimeError", "c2": "invalid_response"}
    # 成功 2 件（c3, c4）と、形式不正で送り直した c2 の 3 回分。送り直した分も課金されるので含める
    assert config["total_token_usage"] == 3 * 2 + 3 * 3


def test_single_child_label_does_not_need_an_api_call(monkeypatch):
    def unexpected(**kwargs):
        pytest.fail("Single-child merge must reuse its existing label")

    monkeypatch.setattr(merge, "request_to_chat_ai", unexpected)
    df = clusters().head(1)
    result = merge.merge_labelling(
        df, ["cluster-level-2-id", "cluster-level-1-id"], {"hierarchical_merge_labelling": {"workers": 1}}
    )
    assert result["cluster-level-1-label"].to_list() == ["one"]


def _length_error():
    from unittest.mock import MagicMock

    import openai

    return openai.LengthFinishReasonError(completion=MagicMock())


@pytest.mark.parametrize("stage", ["initial", "merge"])
@pytest.mark.parametrize("bad", ["broken JSON", "length"])
def test_malformed_response_is_retried_for_that_cluster_only(monkeypatch, stage, bad):
    """1 クラスタの形式不正・途中切れ（出力の上限まで繰り返す応答など）で全体を止めず、そのクラスタだけ送り直す。"""
    calls = {"count": 0}

    def request(**kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            if bad == "length":
                raise _length_error()
            return bad, 2, 1, 3
        return '{"label":"label","description":"description"}', 2, 1, 3

    monkeypatch.setattr(initial if stage == "initial" else merge, "request_to_chat_ai", request)
    config = {
        "provider": "openai",
        "hierarchical_merge_labelling": {"sampling_num": 1, "prompt": "p", "model": "m", "workers": 1},
    }
    result = run_batch(stage, config)
    expected_calls = 4 if stage == "initial" else 2
    assert calls["count"] == expected_calls + 1
    assert len(result) > 0


@pytest.mark.parametrize("stage", ["initial", "merge"])
def test_persistent_length_error_fails_after_retries(monkeypatch, stage):
    from analysis_core.steps._labelling import LABELLING_MALFORMED_RESPONSE_MAX_ATTEMPTS

    calls = {"count": 0}

    def request(**kwargs):
        calls["count"] += 1
        raise _length_error()

    monkeypatch.setattr(initial if stage == "initial" else merge, "request_to_chat_ai", request)
    config = {
        "provider": "openai",
        "hierarchical_merge_labelling": {"sampling_num": 1, "prompt": "p", "model": "m", "workers": 1},
    }
    with pytest.raises(LabellingBatchError) as error:
        run_batch(stage, config)
    clusters_count = 4 if stage == "initial" else 2
    assert calls["count"] == clusters_count * LABELLING_MALFORMED_RESPONSE_MAX_ATTEMPTS
    assert set(error.value.failures.values()) == {"invalid_response"}


@pytest.mark.parametrize("stage", ["initial", "merge"])
def test_api_errors_are_not_retried_here(monkeypatch, stage):
    calls = {"count": 0}

    def request(**kwargs):
        calls["count"] += 1
        raise RuntimeError("private API failure")

    monkeypatch.setattr(initial if stage == "initial" else merge, "request_to_chat_ai", request)
    config = {
        "provider": "openai",
        "hierarchical_merge_labelling": {"sampling_num": 1, "prompt": "p", "model": "m", "workers": 1},
    }
    with pytest.raises(LabellingBatchError):
        run_batch(stage, config)
    assert calls["count"] == (4 if stage == "initial" else 2)


@pytest.mark.parametrize("module", [initial, merge])
def test_label_schema_has_no_top_level_description(module):
    """スキーマの description（クラスの docstring）があると gpt-4o が制御文字を繰り返すことがあるので付けない。"""
    schema = module.LabellingFromat.model_json_schema()
    assert "description" not in schema
    assert set(schema["properties"]) == {"label", "description"}


@pytest.mark.parametrize("stage", ["initial", "merge"])
def test_usage_of_length_cut_attempts_is_counted(monkeypatch, stage):
    """途中切れの応答も課金されているので、送り直す前の回の usage も集計に含める。"""
    from types import SimpleNamespace
    from unittest.mock import MagicMock

    import openai

    calls = {"count": 0}

    def request(**kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            completion = MagicMock()
            completion.usage = SimpleNamespace(prompt_tokens=100, completion_tokens=16384, total_tokens=16484)
            raise openai.LengthFinishReasonError(completion=completion)
        return '{"label":"label","description":"description"}', 2, 1, 3

    monkeypatch.setattr(initial if stage == "initial" else merge, "request_to_chat_ai", request)
    config = {
        "provider": "openai",
        "hierarchical_merge_labelling": {"sampling_num": 1, "prompt": "p", "model": "m", "workers": 1},
    }
    run_batch(stage, config)
    successes = 4 if stage == "initial" else 2
    assert config["total_token_usage"] == 16484 + 3 * successes
    assert config["token_usage_output"] == 16384 + 1 * successes


def test_usage_of_schema_mismatch_attempts_is_counted_through_the_real_sdk(monkeypatch):
    """SDK の parse がスキーマ違反を ValidationError で弾いた回も、課金済みの usage を集計に含める（#1128）。

    SDK は ValidationError に usage を付けないので、偽物の例外ではなく実際の SDK に HTTP 応答を返して確かめる。
    """
    import threading

    import httpx

    llm = importlib.import_module("analysis_core.services.llm")
    lock = threading.Lock()
    calls = {"count": 0}

    def body(content, prompt_tokens, completion_tokens):
        return {
            "id": "x",
            "object": "chat.completion",
            "created": 0,
            "model": "gpt-4o-mini",
            "choices": [{"index": 0, "finish_reason": "stop", "message": {"role": "assistant", "content": content}}],
            "usage": {
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "total_tokens": prompt_tokens + completion_tokens,
            },
        }

    def handler(request: httpx.Request) -> httpx.Response:
        with lock:
            calls["count"] += 1
            first = calls["count"] == 1
        if first:
            # description が無いのでスキーマ違反
            return httpx.Response(200, json=body('{"label": "label"}', 100, 50))
        return httpx.Response(200, json=body('{"label": "label", "description": "description"}', 2, 1))

    monkeypatch.setattr(llm, "chat_http_client", lambda: httpx.Client(transport=httpx.MockTransport(handler)))
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_USE_FLEX", "0")
    config = {"provider": "openai"}

    run_batch("initial", config)

    assert calls["count"] == 5
    assert config["total_token_usage"] == 150 + 3 * 4
    assert config["token_usage_input"] == 100 + 2 * 4
    assert config["token_usage_output"] == 50 + 1 * 4
