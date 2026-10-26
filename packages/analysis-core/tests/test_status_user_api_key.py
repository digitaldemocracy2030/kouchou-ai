"""hierarchical_status.json とユーザー API キーの受け渡しに関するテスト。"""

import importlib
import json
import pickle

import numpy as np
import polars as pl
import pytest

SECRET = "sk-user-SECRET-KEY-1234"


def _read_status(output_base_dir, dataset="demo"):
    return json.loads((output_base_dir / dataset / "hierarchical_status.json").read_text(encoding="utf-8"))


def test_update_status_does_not_write_user_api_key(tmp_path):
    from analysis_core.core import update_status

    (tmp_path / "demo").mkdir()
    config = {
        "output_dir": "demo",
        "user_api_key": SECRET,
        "previous": {
            "user_api_key": SECRET,
            "status": "completed",
            "completed_jobs": [{"step": "extraction", "params": {"user_api_key": SECRET}}],
        },
    }

    update_status(config, {"status": "running"}, tmp_path)

    status_text = (tmp_path / "demo" / "hierarchical_status.json").read_text(encoding="utf-8")
    assert SECRET not in status_text
    status = json.loads(status_text)
    assert status["status"] == "running"
    # previous は入れ子にせず previously_completed_jobs に畳む。その中のキーも除く
    assert "previous" not in status
    assert status["previously_completed_jobs"] == [{"step": "extraction", "params": {}}]
    # ステップに渡すためのメモリ上の config からは消さない
    assert config["user_api_key"] == SECRET
    assert config["previous"]["user_api_key"] == SECRET


def test_update_status_strips_user_api_key_inside_tuples(tmp_path):
    """tuple の中の dict も、キーを除いてから status に書き出す。"""
    from analysis_core.core import update_status

    (tmp_path / "demo").mkdir()
    config = {
        "output_dir": "demo",
        "extra": ({"user_api_key": SECRET, "keep": 1}, ("nested", {"user_api_key": SECRET})),
    }

    update_status(config, {"status": "running"}, tmp_path)
    status_text = (tmp_path / "demo" / "hierarchical_status.json").read_text(encoding="utf-8")
    assert SECRET not in status_text
    assert json.loads(status_text)["extra"] == [{"keep": 1}, ["nested", {}]]
    # メモリ上の config からは消さない
    assert config["extra"][0]["user_api_key"] == SECRET


def test_update_progress_with_legacy_config_keeps_orchestrator_status(tmp_path):
    """縮小版 legacy_config の進捗更新で、本体 config の status を丸ごと上書きしない。"""
    from analysis_core.core import update_progress, update_status
    from analysis_core.plugin import StepContext
    from analysis_core.plugins.builtin._legacy_config import build_legacy_runtime_config

    output_base_dir = tmp_path / "outputs"
    (output_base_dir / "demo").mkdir(parents=True)
    main_config = {
        "output_dir": "demo",
        "_output_base_dir": str(output_base_dir),
        "plan": [{"step": "extraction", "run": True, "reason": "no trace of previous run"}],
        "previous": {"status": "completed", "completed_jobs": [{"step": "extraction"}]},
        "completed_jobs": [],
    }
    update_status(main_config, {"status": "running", "current_job": "extraction"}, output_base_dir)

    ctx = StepContext(
        output_dir=output_base_dir / "demo",
        input_dir=tmp_path / "inputs",
        dataset="demo",
        provider="openai",
        model="gpt-4o-mini",
        user_api_key=SECRET,
    )
    legacy_config = build_legacy_runtime_config(ctx, include_token_usage=True)
    assert legacy_config["user_api_key"] == SECRET

    update_progress(legacy_config, total=4)
    update_progress(legacy_config, incr=3)

    status_text = (output_base_dir / "demo" / "hierarchical_status.json").read_text(encoding="utf-8")
    assert SECRET not in status_text
    status = json.loads(status_text)
    assert status["status"] == "running"
    assert status["current_job"] == "extraction"
    assert status["plan"] == main_config["plan"]
    assert status["previously_completed_jobs"] == [{"step": "extraction"}]
    assert status["completed_jobs"] == []
    assert status["current_jop_tasks"] == 4
    assert status["current_job_progress"] == 3
    assert "lock_until" in status
    assert legacy_config["current_job_progress"] == 3


def test_run_workflow_status_during_step_keeps_lock_and_hides_user_api_key(tmp_path, monkeypatch):
    """workflow 実行中（抽出の進捗更新後）も status / lock が残り、キーが書かれない。"""
    from analysis_core import PipelineOrchestrator
    from analysis_core.core import initialization, update_progress
    from analysis_core.plugin import StepOutputs
    from analysis_core.plugins.builtin._legacy_config import build_legacy_runtime_config
    from analysis_core.workflow.definition import StepResult as WorkflowStepResult
    from analysis_core.workflow.definition import WorkflowResult

    monkeypatch.setenv("USER_API_KEY", SECRET)
    output_base_dir = tmp_path / "outputs"
    orchestrator = PipelineOrchestrator.from_dict(
        config={"name": "demo", "input": "demo", "question": "Test?", "provider": "local", "model": "dummy"},
        output_dir="demo",
        output_base_dir=output_base_dir,
        input_base_dir=tmp_path / "inputs",
    )

    seen = {}

    class FakeEngine:
        def run(self, workflow, config, ctx, on_step_start=None, on_step_complete=None, skip_steps=None):
            assert ctx.user_api_key == SECRET
            on_step_start("extraction")
            legacy_config = build_legacy_runtime_config(ctx, include_token_usage=True)
            update_progress(legacy_config, total=2)
            update_progress(legacy_config, incr=1)
            seen["status_text"] = (output_base_dir / "demo" / "hierarchical_status.json").read_text(encoding="utf-8")
            # 実行中に同じ job を別に起動すると lock で止まる
            config_path = tmp_path / "demo.json"
            config_path.write_text(
                json.dumps({"input": "demo", "question": "Test?", "provider": "local"}), encoding="utf-8"
            )
            with pytest.raises(Exception, match="Job already running"):
                initialization(
                    config_path=config_path,
                    skip_interaction=True,
                    output_base_dir=output_base_dir,
                    input_base_dir=tmp_path / "inputs",
                )

            step_result = WorkflowStepResult(step_id="extraction", success=True, outputs=StepOutputs())
            on_step_complete("extraction", step_result)
            result = WorkflowResult(workflow_id="test")
            result.step_results["extraction"] = step_result
            return result

    monkeypatch.setattr("analysis_core.workflow.WorkflowEngine", FakeEngine)

    assert orchestrator.run_workflow().success is True

    assert SECRET not in seen["status_text"]
    status = json.loads(seen["status_text"])
    assert status["status"] == "running"
    assert status["current_job"] == "extraction"
    assert status["plan"]
    assert status["current_job_progress"] == 1
    assert SECRET not in (output_base_dir / "demo" / "hierarchical_status.json").read_text(encoding="utf-8")


def test_from_dict_does_not_persist_config_user_api_key(tmp_path, monkeypatch):
    from analysis_core import PipelineOrchestrator
    from analysis_core.workflow.definition import WorkflowResult

    output_base_dir = tmp_path / "outputs"
    orchestrator = PipelineOrchestrator.from_dict(
        config={
            "name": "demo",
            "input": "demo",
            "question": "Test?",
            "provider": "openai",
            "model": "dummy",
            "user_api_key": SECRET,
        },
        output_dir="demo",
        output_base_dir=output_base_dir,
        input_base_dir=tmp_path / "inputs",
    )

    class FakeEngine:
        def run(self, workflow, config, ctx, on_step_start=None, on_step_complete=None, skip_steps=None):
            assert ctx.user_api_key == SECRET
            return WorkflowResult(workflow_id="test")

    monkeypatch.setattr("analysis_core.workflow.WorkflowEngine", FakeEngine)
    orchestrator.run_workflow()

    assert SECRET not in (output_base_dir / "demo" / "hierarchical_status.json").read_text(encoding="utf-8")


def _write_job_config(tmp_path, provider):
    config_path = tmp_path / "job.json"
    config_path.write_text(json.dumps({"input": "test", "question": "Test?", "provider": provider}))
    (tmp_path / "inputs").mkdir(exist_ok=True)
    return config_path


@pytest.mark.parametrize("provider", ["openai", "gemini", "openrouter"])
def test_initialization_skips_api_key_validation_when_only_aggregation_runs(tmp_path, monkeypatch, provider):
    """集計だけの再実行（LLM を使わない）ではキー検査で止めない。"""
    from analysis_core.core import initialization

    for name in ("OPENAI_API_KEY", "GEMINI_API_KEY", "OPENROUTER_API_KEY", "USER_API_KEY"):
        monkeypatch.setenv(name, "")
    monkeypatch.setattr("analysis_core.core.orchestration.load_env_file", lambda **_: None)

    config = initialization(
        config_path=_write_job_config(tmp_path, provider),
        only="hierarchical_aggregation",
        skip_interaction=True,
        validate_api_keys_early=True,
        output_base_dir=tmp_path / "outputs",
        input_base_dir=tmp_path / "inputs",
    )

    assert [s["step"] for s in config["plan"] if s["run"]] == ["hierarchical_aggregation"]


def test_initialization_still_validates_api_keys_when_llm_step_runs(tmp_path, monkeypatch):
    from analysis_core.core import initialization

    monkeypatch.setenv("GEMINI_API_KEY", "")
    monkeypatch.setenv("USER_API_KEY", "")
    monkeypatch.setattr("analysis_core.core.orchestration.load_env_file", lambda **_: None)

    with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
        initialization(
            config_path=_write_job_config(tmp_path, "gemini"),
            only="hierarchical_overview",
            skip_interaction=True,
            validate_api_keys_early=True,
            output_base_dir=tmp_path / "outputs",
            input_base_dir=tmp_path / "inputs",
        )
    # 検査で止めた場合は running の status を残さない
    assert not (tmp_path / "outputs" / "job" / "hierarchical_status.json").exists()


def test_from_dict_skips_api_key_validation_when_plan_has_no_llm_step(tmp_path, monkeypatch):
    from analysis_core import PipelineOrchestrator

    monkeypatch.setenv("GEMINI_API_KEY", "")
    monkeypatch.setenv("USER_API_KEY", "")
    monkeypatch.setattr("analysis_core.core.orchestration.load_env_file", lambda **_: None)
    plan = [
        {"step": "extraction", "run": False, "reason": "forced another step with -o"},
        {"step": "hierarchical_aggregation", "run": True, "reason": "forced this step with -o"},
    ]
    base = {"name": "demo", "input": "demo", "question": "Test?", "provider": "gemini", "model": "dummy"}

    orchestrator = PipelineOrchestrator.from_dict(
        config={**base, "plan": plan}, output_dir="demo", output_base_dir=tmp_path / "outputs"
    )
    assert orchestrator.get_plan() == plan

    with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
        PipelineOrchestrator.from_dict(config=base, output_dir="demo2", output_base_dir=tmp_path / "outputs")


def _prepare_llm_grouping(tmp_path, monkeypatch):
    llm_grouping_step = importlib.import_module("analysis_core.steps.llm_grouping")
    output_dir = tmp_path / "outputs" / "demo"
    output_dir.mkdir(parents=True)
    pl.DataFrame({"arg-id": ["a1", "a2"], "argument": ["電車を増やして", "公園を増やして"]}).write_csv(
        output_dir / "args.csv"
    )
    with open(output_dir / "embeddings.pkl", "wb") as f:
        pickle.dump([{"arg-id": "a1", "embedding": [0.1, 0.2]}, {"arg-id": "a2", "embedding": [0.9, 0.8]}], f)

    class FakeUMAP:
        def __init__(self, n_components, n_neighbors):
            pass

        def fit_transform(self, embeddings):
            return np.array([[0.0, 0.0], [1.0, 1.0]])

    monkeypatch.setattr(llm_grouping_step, "_load_clustering_dependencies", lambda: (FakeUMAP, None, None))

    calls = []
    responses = [
        {"groups": [{"label": "交通", "description": ""}, {"label": "公園", "description": ""}]},
        {"assignments": [{"arg_id": "a1", "group_id": "g1"}, {"arg_id": "a2", "group_id": "g2"}]},
    ]

    def fake_request_to_chat_ai(**kwargs):
        calls.append(kwargs)
        return responses.pop(0), 1, 1, 2

    monkeypatch.setattr(llm_grouping_step, "request_to_chat_ai", fake_request_to_chat_ai)
    config = {
        "output_dir": "demo",
        "_output_base_dir": str(tmp_path / "outputs"),
        "question": "問い",
        "provider": "openai",
        "llm_grouping": {
            "group_count": 2,
            "assignment_batch_size": 10,
            "discovery_prompt": "discover",
            "assignment_prompt": "assign",
            "model": "dummy-model",
        },
    }
    return llm_grouping_step, config, calls


def test_llm_grouping_uses_user_api_key_from_config(tmp_path, monkeypatch):
    llm_grouping_step, config, calls = _prepare_llm_grouping(tmp_path, monkeypatch)
    monkeypatch.delenv("USER_API_KEY", raising=False)
    config["user_api_key"] = SECRET

    llm_grouping_step.llm_grouping(config)

    assert len(calls) == 2
    assert [c["user_api_key"] for c in calls] == [SECRET, SECRET]


def test_llm_grouping_falls_back_to_env_user_api_key(tmp_path, monkeypatch):
    llm_grouping_step, config, calls = _prepare_llm_grouping(tmp_path, monkeypatch)
    monkeypatch.setenv("USER_API_KEY", "env-user-key")

    llm_grouping_step.llm_grouping(config)

    assert [c["user_api_key"] for c in calls] == ["env-user-key", "env-user-key"]
