"""Tests for the LLM grouping workflow mode."""

import importlib
import json
import pickle

import numpy as np
import polars as pl
import pytest

from analysis_core.orchestrator import PipelineOrchestrator


def test_run_workflow_uses_llm_grouping_workflow_when_mode_is_enabled(tmp_path, monkeypatch):
    """Workflow selection should honor analysis_mode=llm_grouping."""
    from analysis_core.workflow.definition import StepResult as WorkflowStepResult
    from analysis_core.workflow.definition import WorkflowResult

    orchestrator = PipelineOrchestrator.from_dict(
        config={
            "name": "demo",
            "input": "demo",
            "question": "Test?",
            "provider": "local",
            "model": "dummy",
            "analysis_mode": "llm_grouping",
        },
        output_dir="demo",
        output_base_dir=tmp_path / "outputs",
        input_base_dir=tmp_path / "inputs",
    )

    seen = {}

    class FakeEngine:
        def run(self, workflow, config, ctx, on_step_start=None, on_step_complete=None, skip_steps=None):
            seen["workflow_id"] = workflow.id
            result = WorkflowResult(workflow_id=workflow.id)
            step_result = WorkflowStepResult(step_id="llm_grouping", success=True)
            result.step_results["llm_grouping"] = step_result
            if on_step_start:
                on_step_start("llm_grouping")
            if on_step_complete:
                on_step_complete("llm_grouping", step_result)
            return result

    monkeypatch.setattr("analysis_core.workflow.WorkflowEngine", FakeEngine)

    result = orchestrator.run_workflow()

    assert seen["workflow_id"] == "llm-grouping-compatible"
    assert [step.step_name for step in result.steps] == ["llm_grouping"]


def test_get_specs_path_for_mode_rejects_unknown_mode():
    """Unknown analysis modes should fail fast instead of silently falling back."""
    from analysis_core.core.orchestration import get_specs_path_for_mode

    with pytest.raises(ValueError, match="Unknown analysis_mode: unexpected_mode"):
        get_specs_path_for_mode("unexpected_mode")


def test_llm_grouping_specs_treat_prompt_changes_as_dependencies():
    """Prompt fields must participate in rerun invalidation."""
    from analysis_core.core.orchestration import get_specs_path_for_mode

    specs_path = get_specs_path_for_mode("llm_grouping")
    specs = json.loads(specs_path.read_text(encoding="utf-8"))
    llm_grouping_spec = next(spec for spec in specs if spec["step"] == "llm_grouping")

    assert "discovery_prompt" in llm_grouping_spec["dependencies"]["params"]
    assert "assignment_prompt" in llm_grouping_spec["dependencies"]["params"]


def test_llm_grouping_step_creates_viewer_compatible_outputs(tmp_path, monkeypatch):
    """The step should cluster arguments directly with LLM and preserve embedding-based coordinates."""
    llm_grouping_step = importlib.import_module("analysis_core.steps.llm_grouping")

    output_dir = tmp_path / "outputs" / "demo"
    output_dir.mkdir(parents=True)
    args_df = pl.DataFrame(
        {
            "arg-id": ["a1", "a2", "a3"],
            "argument": ["電車を増やしてほしい", "バスの本数が足りない", "公園を増やしてほしい"],
        }
    )
    args_df.write_csv(output_dir / "args.csv")
    with open(output_dir / "embeddings.pkl", "wb") as f:
        pickle.dump(
            [
                {"arg-id": "a1", "embedding": [0.1, 0.2, 0.3]},
                {"arg-id": "a2", "embedding": [0.2, 0.1, 0.3]},
                {"arg-id": "a3", "embedding": [0.9, 0.8, 0.7]},
            ],
            f,
        )

    class FakeUMAP:
        def __init__(self, n_components, n_neighbors):
            self.n_components = n_components
            self.n_neighbors = n_neighbors

        def fit_transform(self, embeddings):
            return np.array([[0.0, 0.0], [1.0, 0.0], [0.0, 1.0]])

    monkeypatch.setattr(llm_grouping_step, "_load_clustering_dependencies", lambda: (FakeUMAP, None, None))

    responses = [
        {
            "groups": [
                {"group_id": "g1", "label": "交通", "description": "公共交通に関する意見"},
                {"group_id": "g2", "label": "公園", "description": "公園整備に関する意見"},
            ]
        },
        {
            "assignments": [
                {"arg_id": "a1", "group_id": "g1"},
                {"arg_id": "a2", "group_id": "g1"},
            ]
        },
        {
            "assignments": [
                {"arg_id": "a3", "group_id": "g2"},
            ]
        },
    ]

    def fake_request_to_chat_ai(**kwargs):
        response = responses.pop(0)
        return response, 10, 5, 15

    monkeypatch.setattr(llm_grouping_step, "request_to_chat_ai", fake_request_to_chat_ai)

    config = {
        "output_dir": "demo",
        "_output_base_dir": str(tmp_path / "outputs"),
        "question": "住みやすい街にするには？",
        "provider": "local",
        "llm_grouping": {
            "group_count": 2,
            "discovery_sample_size": 3,
            "assignment_batch_size": 2,
            "discovery_prompt": "discover",
            "assignment_prompt": "assign",
            "model": "dummy-model",
        },
        "hierarchical_clustering": {"cluster_nums": [2, 4]},
    }

    llm_grouping_step.llm_grouping(config)

    clusters = pl.read_csv(output_dir / "hierarchical_clusters.csv")
    labels = pl.read_csv(output_dir / "hierarchical_merge_labels.csv")

    assert clusters.columns == ["arg-id", "argument", "x", "y", "cluster-level-1-id"]
    assert clusters["cluster-level-1-id"].to_list() == ["g1", "g1", "g2"]
    assert labels.select(["id", "label"]).to_dict(as_series=False) == {"id": ["g1", "g2"], "label": ["交通", "公園"]}
    assert config["total_token_usage"] == 45


def test_llm_grouping_uses_legacy_embedding_order_when_arg_ids_are_missing(tmp_path, monkeypatch):
    """Legacy embedding lists without arg-id keys should fall back to positional matching."""
    llm_grouping_step = importlib.import_module("analysis_core.steps.llm_grouping")

    output_dir = tmp_path / "outputs" / "demo"
    output_dir.mkdir(parents=True)
    with open(output_dir / "embeddings.pkl", "wb") as f:
        pickle.dump(
            [
                {"embedding": [0.1, 0.2, 0.3]},
                {"embedding": [0.2, 0.1, 0.3]},
            ],
            f,
        )

    class FakeUMAP:
        def __init__(self, n_components, n_neighbors):
            self.n_components = n_components
            self.n_neighbors = n_neighbors

        def fit_transform(self, embeddings):
            return np.asarray(embeddings[:, :2])

    monkeypatch.setattr(llm_grouping_step, "_load_clustering_dependencies", lambda: (FakeUMAP, None, None))

    result = llm_grouping_step._project_embeddings_to_xy(str(tmp_path / "outputs"), "demo", ["a1", "a2"])
    assert result.shape == (2, 2)


def test_llm_grouping_reports_missing_embedding_arg_ids(tmp_path):
    """Missing embeddings should raise a clear error with the missing ids."""
    llm_grouping_step = importlib.import_module("analysis_core.steps.llm_grouping")

    output_dir = tmp_path / "outputs" / "demo"
    output_dir.mkdir(parents=True)
    with open(output_dir / "embeddings.pkl", "wb") as f:
        pickle.dump([{"arg-id": "a1", "embedding": [0.1, 0.2, 0.3]}], f)

    with pytest.raises(ValueError, match=r"Missing embeddings for arg ids: \['a2'\]"):
        llm_grouping_step._project_embeddings_to_xy(str(tmp_path / "outputs"), "demo", ["a1", "a2"])


def test_assign_groups_uses_safe_batch_size_for_non_positive_input(monkeypatch):
    """Non-positive batch sizes should still process all arguments consistently."""
    llm_grouping_step = importlib.import_module("analysis_core.steps.llm_grouping")

    captured_messages = []

    def fake_request_to_chat_ai(**kwargs):
        captured_messages.append(kwargs["messages"][1]["content"])
        arg_id = f"a{len(captured_messages)}"
        return {"assignments": [{"arg_id": arg_id, "group_id": "g1"}]}, 0, 0, 0

    monkeypatch.setattr(llm_grouping_step, "request_to_chat_ai", fake_request_to_chat_ai)

    groups = [llm_grouping_step.GroupDefinition(group_id="g1", label="交通", description="公共交通")]
    assignments = llm_grouping_step._assign_groups(
        arg_ids=["a1", "a2"],
        arguments=["電車", "バス"],
        groups=groups,
        batch_size=0,
        prompt="assign",
        model="dummy-model",
        provider="local",
        local_llm_address=None,
        config={},
    )

    assert assignments == {"a1": "g1", "a2": "g1"}
    assert len(captured_messages) == 2
