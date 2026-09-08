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
    assert config["total_token_usage"] == 9


def test_single_child_label_does_not_need_an_api_call(monkeypatch):
    def unexpected(**kwargs):
        pytest.fail("Single-child merge must reuse its existing label")

    monkeypatch.setattr(merge, "request_to_chat_ai", unexpected)
    df = clusters().head(1)
    result = merge.merge_labelling(
        df, ["cluster-level-2-id", "cluster-level-1-id"], {"hierarchical_merge_labelling": {"workers": 1}}
    )
    assert result["cluster-level-1-label"].to_list() == ["one"]
