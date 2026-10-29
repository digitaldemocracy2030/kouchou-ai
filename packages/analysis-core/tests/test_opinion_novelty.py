"""Opinion novelty score: ranking, methods, embeddings alignment, output files, aggregation merge, pipeline wiring."""

import importlib
import json
import pickle

import numpy as np
import polars as pl
import pytest

novelty = importlib.import_module("analysis_core.steps.opinion_novelty")
aggregation = importlib.import_module("analysis_core.steps.hierarchical_aggregation")


class TestRank:
    def test_percentile_rank_is_monotone_and_handles_ties(self):
        ranks = novelty.percentile_rank(np.array([0.1, 0.3, 0.3, 0.9]))
        assert ranks[0] == 0.0 and ranks[3] == 1.0
        assert ranks[1] == ranks[2] == pytest.approx(0.5)

    def test_single_or_empty_input(self):
        assert novelty.percentile_rank(np.array([0.5])).tolist() == [0.0]
        assert novelty.percentile_rank(np.array([])).tolist() == []


def _embeddings():
    # 3 件はほぼ同じ向き、1 件だけ直交（= 他から遠い）
    return np.array(
        [[1.0, 0.0, 0.0], [0.99, 0.1, 0.0], [0.98, 0.0, 0.1], [0.0, 0.0, 1.0]],
        dtype=np.float32,
    )


class TestCompute:
    def test_knn_marks_the_outlier_highest(self):
        scores, raw = novelty.compute_novelty(_embeddings(), method="knn_distance", k=2)
        assert scores[3] == 1.0
        assert max(scores[:3]) < 1.0
        assert raw[3] > max(raw[:3])

    def test_k_is_clipped_to_n_minus_one(self):
        scores, _ = novelty.compute_novelty(_embeddings(), method="knn_distance", k=100)
        assert scores[3] == 1.0

    def test_isolation_forest_is_deterministic_for_a_seed(self):
        a, _ = novelty.compute_novelty(_embeddings(), method="isolation_forest", seed=1)
        b, _ = novelty.compute_novelty(_embeddings(), method="isolation_forest", seed=1)
        assert a.tolist() == b.tolist()
        assert all(0.0 <= s <= 1.0 for s in a)

    def test_unknown_method_is_rejected(self):
        with pytest.raises(ValueError, match="method"):
            novelty.compute_novelty(_embeddings(), method="magic")

    def test_fewer_than_two_opinions_score_zero(self):
        scores, _ = novelty.compute_novelty(_embeddings()[:1], method="knn_distance")
        assert scores.tolist() == [0.0]


class TestAlignment:
    def test_rows_follow_args_order_by_arg_id(self, tmp_path):
        path = tmp_path / "embeddings.pkl"
        records = [
            {"arg-id": "B", "embedding": np.array([0.0, 1.0], dtype=np.float32)},
            {"arg-id": "A", "embedding": np.array([1.0, 0.0], dtype=np.float32)},
        ]
        path.write_bytes(pickle.dumps(records))
        matrix = novelty.load_aligned_embeddings(str(path), ["A", "B"])
        assert matrix.tolist() == [[1.0, 0.0], [0.0, 1.0]]

    def test_missing_arg_id_is_an_error(self, tmp_path):
        path = tmp_path / "embeddings.pkl"
        path.write_bytes(pickle.dumps([{"arg-id": "A", "embedding": np.array([1.0], dtype=np.float32)}]))
        with pytest.raises(ValueError, match="arg-id"):
            novelty.load_aligned_embeddings(str(path), ["A", "C"])


def _write_report(tmp_path, embeddings):
    out = tmp_path / "report"
    out.mkdir()
    arg_ids = [f"A{i}_0" for i in range(len(embeddings))]
    pl.DataFrame({"arg-id": arg_ids, "argument": ["t"] * len(arg_ids)}).write_csv(out / "args.csv")
    records = [{"arg-id": a, "embedding": np.asarray(e, dtype=np.float32)} for a, e in zip(arg_ids, embeddings)]
    (out / "embeddings.pkl").write_bytes(pickle.dumps(records))
    return out


def _config(tmp_path, **overrides):
    config = {"output_dir": "report", "_output_base_dir": str(tmp_path), "opinion_novelty": {"k": 2}}
    config["opinion_novelty"].update(overrides)
    return config


class TestStep:
    def test_writes_csv_and_summary(self, tmp_path, monkeypatch):
        out = _write_report(tmp_path, _embeddings())
        monkeypatch.setattr(novelty, "update_progress", lambda *args, **kwargs: None)
        novelty.opinion_novelty(_config(tmp_path))

        frame = pl.read_csv(out / "opinion_novelty.csv")
        assert frame.columns == ["arg-id", "novelty_score"]
        assert frame["arg-id"].to_list() == ["A0_0", "A1_0", "A2_0", "A3_0"]
        assert frame["novelty_score"].to_list()[3] == 1.0

        summary = json.loads((out / "opinion_novelty_summary.json").read_text(encoding="utf-8"))
        assert summary["total"] == 4
        assert summary["method"] == "knn_distance" and summary["params"] == {"k": 2}
        assert summary["raw_value"]["max"] > summary["raw_value"]["min"]
        assert "検証" in summary["note"]

    def test_isolation_forest_params_in_summary(self, tmp_path, monkeypatch):
        out = _write_report(tmp_path, _embeddings())
        monkeypatch.setattr(novelty, "update_progress", lambda *args, **kwargs: None)
        novelty.opinion_novelty(_config(tmp_path, method="isolation_forest", seed=7))
        summary = json.loads((out / "opinion_novelty_summary.json").read_text(encoding="utf-8"))
        assert summary["method"] == "isolation_forest" and summary["params"] == {"seed": 7}

    def test_failure_removes_previous_output(self, tmp_path, monkeypatch):
        out = _write_report(tmp_path, _embeddings())
        (out / "opinion_novelty.csv").write_text("arg-id,novelty_score\nOLD,1\n", encoding="utf-8")
        monkeypatch.setattr(novelty, "update_progress", lambda *args, **kwargs: None)
        with pytest.raises(ValueError, match="method"):
            novelty.opinion_novelty(_config(tmp_path, method="magic"))
        assert not (out / "opinion_novelty.csv").exists()


class TestAggregationMerge:
    def test_scores_are_added_as_numbers(self, tmp_path):
        path = tmp_path / "opinion_novelty.csv"
        pl.DataFrame({"arg-id": ["A1_0", "A2_0"], "novelty_score": [0.25, 1.0]}).write_csv(path)
        arguments = [
            {"arg_id": "A1_0", "argument": "x", "attributes": {"age": "20s"}},
            {"arg_id": "A2_0", "argument": "y", "attributes": None},
            {"arg_id": "A3_0", "argument": "z", "attributes": None},
        ]
        assert aggregation._merge_opinion_scores(arguments, str(path), "novelty_score") == 2
        assert arguments[0]["attributes"] == {"age": "20s", "novelty_score": 0.25}
        assert arguments[1]["attributes"] == {"novelty_score": 1.0}
        assert arguments[2]["attributes"] is None


class TestPipelineWiring:
    def test_plan_disabled_by_default_and_enabled_on_request(self, tmp_path):
        from analysis_core.core import decide_what_to_run, load_specs
        from analysis_core.core.orchestration import _PACKAGE_DIR

        specs = load_specs(_PACKAGE_DIR / "specs" / "hierarchical_specs.json")
        config = {"input": "test", "question": "Test?", "output_dir": "test"}
        plan = {s["step"]: s for s in decide_what_to_run(config, None, specs, tmp_path)}
        assert plan["opinion_novelty"]["run"] is False
        assert "disabled" in plan["opinion_novelty"]["reason"]

        config["opinion_novelty"] = {"enabled": True}
        plan = {s["step"]: s for s in decide_what_to_run(config, None, specs, tmp_path)}
        assert plan["opinion_novelty"]["run"] is True

        config["force"] = True
        config["opinion_novelty"] = {"enabled": False}
        plan = {s["step"]: s for s in decide_what_to_run(config, None, specs, tmp_path)}
        assert plan["opinion_novelty"]["run"] is False

    def test_workflow_and_registry_include_step(self):
        from analysis_core.plugin import get_registry
        from analysis_core.workflows.hierarchical_default import create_hierarchical_workflow

        workflow = create_hierarchical_workflow()
        step = workflow.get_step("opinion_novelty")
        assert step is not None
        assert step.plugin == "analysis.opinion_novelty"
        assert step.depends_on == ["embedding"]
        assert step.condition == "${config.opinion_novelty.enabled}"
        assert "opinion_novelty" in workflow.get_step("aggregation").depends_on

        registry = get_registry()
        registry.register_builtin_plugins()
        plugin = registry.get("analysis.opinion_novelty")
        assert plugin.metadata.inputs == ["arguments", "embeddings"]
        assert plugin.metadata.use_llm is False

    def test_normalize_config_defaults(self):
        from analysis_core.compat import normalize_config

        step = normalize_config({"model": "gpt-x"}, include_source_code=False)["opinion_novelty"]
        assert step == {"enabled": False, "method": "knn_distance", "k": 10, "seed": 42}

    def test_plugin_runs_impl_and_returns_artifacts(self, tmp_path, monkeypatch):
        from analysis_core.plugin import StepContext, StepInputs
        from analysis_core.plugins.builtin.opinion_novelty import opinion_novelty_plugin

        output_dir = tmp_path / "out" / "demo"
        output_dir.mkdir(parents=True)
        seen = {}
        monkeypatch.setattr(novelty, "opinion_novelty", lambda config: seen.update(config))
        ctx = StepContext(output_dir=output_dir, input_dir=tmp_path / "in", dataset="demo", provider="local", model="m")
        outputs = opinion_novelty_plugin.run(ctx, StepInputs(), {"opinion_novelty": {"method": "knn_distance", "k": 5}})
        assert seen["opinion_novelty"] == {"method": "knn_distance", "k": 5, "seed": None}
        assert outputs.artifacts["novelty"] == output_dir / "opinion_novelty.csv"
