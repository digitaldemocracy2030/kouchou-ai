"""LLM 直接グルーピングの割当を workers 本で並列に呼ぶことの回帰テスト（b007）。

割当（_assign_groups）は assignment_batch_size 件ずつのバッチを 1 回ずつ直列に呼んでいたため、
管理画面の並列数がこのステップに効かず、意見が多いとこのステップだけが極端に遅くなっていた。
"""

import importlib
import json
import re
import threading
import time

import pytest

llm_grouping_step = importlib.import_module("analysis_core.steps.llm_grouping")

GROUPS = [
    llm_grouping_step.GroupDefinition(group_id="g1", label="交通", description="公共交通"),
    llm_grouping_step.GroupDefinition(group_id="g2", label="公園", description="公園整備"),
]


def _batch_arg_ids(kwargs) -> list[str]:
    """割当プロンプトの「意見一覧」から、このバッチの arg_id を取り出す。"""
    content = kwargs["messages"][1]["content"]
    return re.findall(r"^- (a\d+): ", content, flags=re.MULTILINE)


class _ConcurrencyProbe:
    """request_to_chat_ai の代役。同時実行数を数え、バッチの arg_id を偶数→g2・奇数→g1 に割り当てる。"""

    def __init__(self, delay_for=None, fail_on_call=None):
        self.lock = threading.Lock()
        self.active = 0
        self.max_active = 0
        self.calls = 0
        self.delay_for = delay_for or (lambda index: 0.05)
        self.fail_on_call = fail_on_call

    def __call__(self, **kwargs):
        with self.lock:
            self.calls += 1
            call_index = self.calls
            self.active += 1
            self.max_active = max(self.max_active, self.active)
        try:
            batch_ids = _batch_arg_ids(kwargs)
            first = int(batch_ids[0][1:])
            time.sleep(self.delay_for(first))
            if self.fail_on_call is not None and call_index == self.fail_on_call:
                raise TimeoutError("simulated timeout")
            assignments = [
                {"arg_id": arg_id, "group_id": "g2" if int(arg_id[1:]) % 2 == 0 else "g1"} for arg_id in batch_ids
            ]
            return json.dumps({"assignments": assignments}), 3, 2, 5
        finally:
            with self.lock:
                self.active -= 1


def _assign(arg_count, *, batch_size, workers, config=None):
    arg_ids = [f"a{i}" for i in range(arg_count)]
    arguments = [f"意見 {i}" for i in range(arg_count)]
    return arg_ids, llm_grouping_step._assign_groups(
        arg_ids=arg_ids,
        arguments=arguments,
        groups=GROUPS,
        batch_size=batch_size,
        prompt="assign",
        model="dummy-model",
        provider="local",
        local_llm_address=None,
        config={} if config is None else config,
        workers=workers,
    )


def test_assign_groups_runs_batches_concurrently_up_to_workers(monkeypatch):
    probe = _ConcurrencyProbe()
    monkeypatch.setattr(llm_grouping_step, "request_to_chat_ai", probe)

    arg_ids, assignments = _assign(80, batch_size=5, workers=4)

    assert probe.calls == 16
    assert probe.max_active == 4
    assert list(assignments) == arg_ids
    assert assignments == {arg_id: ("g2" if int(arg_id[1:]) % 2 == 0 else "g1") for arg_id in arg_ids}


def test_assign_groups_keeps_input_order_when_batches_finish_out_of_order(monkeypatch):
    # 先頭のバッチほど遅く返す（後ろのバッチが先に終わる）
    probe = _ConcurrencyProbe(delay_for=lambda first: 0.01 * (40 - first) / 5)
    monkeypatch.setattr(llm_grouping_step, "request_to_chat_ai", probe)

    arg_ids, assignments = _assign(40, batch_size=5, workers=8)

    assert list(assignments) == arg_ids
    assert assignments["a0"] == "g2" and assignments["a1"] == "g1" and assignments["a39"] == "g1"


def test_assign_groups_sums_token_usage_of_all_parallel_batches(monkeypatch):
    probe = _ConcurrencyProbe(delay_for=lambda first: 0.001)
    monkeypatch.setattr(llm_grouping_step, "request_to_chat_ai", probe)
    config = {"total_token_usage": 100, "token_usage_input": 60, "token_usage_output": 40}

    _assign(50, batch_size=5, workers=6, config=config)

    assert config == {"total_token_usage": 150, "token_usage_input": 90, "token_usage_output": 60}


def test_assign_groups_with_one_worker_stays_sequential(monkeypatch):
    probe = _ConcurrencyProbe(delay_for=lambda first: 0.005)
    monkeypatch.setattr(llm_grouping_step, "request_to_chat_ai", probe)

    arg_ids, assignments = _assign(30, batch_size=5, workers=1)

    assert probe.max_active == 1
    assert list(assignments) == arg_ids


def test_assign_groups_stops_sending_remaining_batches_after_a_failure(monkeypatch):
    probe = _ConcurrencyProbe(delay_for=lambda first: 0.02, fail_on_call=1)
    monkeypatch.setattr(llm_grouping_step, "request_to_chat_ai", probe)

    with pytest.raises(TimeoutError, match="simulated timeout"):
        _assign(200, batch_size=5, workers=2)

    # 40 バッチのうち、失敗の時点で実行中・取得済みのものだけが送られ、残りは送らない
    assert probe.calls < 10


def test_llm_grouping_step_passes_configured_workers_to_assignment(tmp_path, monkeypatch):
    import numpy as np
    import polars as pl

    output_dir = tmp_path / "outputs" / "demo"
    output_dir.mkdir(parents=True)
    pl.DataFrame({"arg-id": ["a0", "a1"], "argument": ["電車", "公園"]}).write_csv(output_dir / "args.csv")

    seen = {}

    def fake_assign_groups(**kwargs):
        seen.update(kwargs)
        return {"a0": "g1", "a1": "g1"}

    monkeypatch.setattr(llm_grouping_step, "_assign_groups", fake_assign_groups)
    monkeypatch.setattr(llm_grouping_step, "_project_embeddings_to_xy", lambda *_: np.zeros((2, 2)))

    config = {
        "output_dir": "demo",
        "_output_base_dir": str(tmp_path / "outputs"),
        "provider": "local",
        "llm_grouping": {
            "predefined_groups": [{"label": "交通"}],
            "assignment_prompt": "assign",
            "model": "dummy-model",
            "workers": 7,
        },
    }
    llm_grouping_step.llm_grouping(config)
    assert seen["workers"] == 7

    # 未指定・None の config（旧レポートの書き戻しなど）は 1 本で動く
    for missing in ({}, {"workers": None}):
        seen.clear()
        config["llm_grouping"] = {k: v for k, v in config["llm_grouping"].items() if k != "workers"} | missing
        llm_grouping_step.llm_grouping(config)
        assert seen["workers"] == 1


def test_llm_grouping_specs_accept_workers_without_rerunning_on_change():
    from analysis_core.core.orchestration import get_specs_path_for_mode, validate_config

    specs = json.loads(get_specs_path_for_mode("llm_grouping").read_text(encoding="utf-8"))
    spec = next(spec for spec in specs if spec["step"] == "llm_grouping")

    assert spec["options"]["workers"] == 1
    # 並列数は結果を変えないので、変えても割当をやり直さない
    assert "workers" not in spec["dependencies"]["params"]
    validate_config(
        {"input": "demo", "question": "q", "analysis_mode": "llm_grouping", "llm_grouping": {"workers": 8}},
        specs,
    )


def test_llm_grouping_workflow_and_plugin_forward_workers(tmp_path, monkeypatch):
    from analysis_core.plugin import StepContext, StepInputs
    from analysis_core.plugins.builtin.llm_grouping import llm_grouping_plugin
    from analysis_core.workflows.llm_grouping_compatible import create_llm_grouping_workflow

    workflow = create_llm_grouping_workflow(include_visualization=False)
    step = next(step for step in workflow.steps if step.id == "llm_grouping")
    assert step.config["workers"] == "${config.llm_grouping.workers}"

    output_dir = tmp_path / "out" / "demo"
    output_dir.mkdir(parents=True)
    ctx = StepContext(output_dir=output_dir, input_dir=tmp_path / "in", dataset="demo", provider="local", model="m")
    seen = {}
    monkeypatch.setattr(llm_grouping_step, "llm_grouping", lambda config: seen.update(config["llm_grouping"]))

    llm_grouping_plugin.run(ctx, StepInputs(config={}), {"assignment_batch_size": 25, "workers": 6})

    assert seen["workers"] == 6


def test_normalize_config_fills_llm_grouping_workers_default():
    from analysis_core.compat import normalize_config

    assert normalize_config({})["llm_grouping"]["workers"] == 1
    assert normalize_config({"llm_grouping": {"workers": 4}})["llm_grouping"]["workers"] == 4
