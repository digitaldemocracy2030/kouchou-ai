"""Exercise reproducible clustering through the CLI workflow with saved inputs."""

import json
import pickle
import sys
from importlib import import_module

import numpy as np
import polars as pl
import pytest

from analysis_core.__main__ import main
from analysis_core.compat import normalize_config
from analysis_core.core.orchestration import get_specs_path_for_mode, load_specs, validate_config
from analysis_core.orchestrator import PipelineOrchestrator
from analysis_core.prompts import get_default_prompt


@pytest.fixture
def saved_inputs(tmp_path):
    source = tmp_path / "outputs" / "baseline"
    source.mkdir(parents=True)
    arg_ids = [f"A{i}_0" for i in range(30)]
    pl.DataFrame({"arg-id": arg_ids, "argument": [f"意見 {i}" for i in range(len(arg_ids))]}).write_csv(
        source / "args.csv"
    )
    pl.DataFrame({"arg-id": arg_ids, "comment-id": [str(i) for i in range(len(arg_ids))]}).write_csv(
        source / "relations.csv"
    )
    rng = np.random.default_rng(8)
    with (source / "embeddings.pkl").open("wb") as file:
        pickle.dump([{"arg-id": arg_id, "embedding": rng.normal(size=12).tolist()} for arg_id in arg_ids], file)
    (source / "hierarchical_status.json").write_text(
        json.dumps(
            {
                "status": "completed",
                "completed_jobs": [
                    {
                        "step": "extraction",
                        "params": {"model": "gpt-4o-mini", "prompt": get_default_prompt("extraction")},
                        "global_params": {"input": "source"},
                    },
                    {"step": "embedding", "params": {"model": "text-embedding-3-small"}},
                ],
            }
        )
    )
    return source


@pytest.mark.parametrize(
    ("mode", "step"),
    [("hierarchical", "hierarchical_clustering"), ("llm_grouping", "llm_grouping")],
)
def test_seeded_cli_uses_saved_inputs_and_records_seed(tmp_path, saved_inputs, monkeypatch, mode, step):
    # Keep the LLM assignments fixed to isolate the actual UMAP projection.
    if mode == "llm_grouping":
        monkeypatch.setattr(
            import_module("analysis_core.steps.llm_grouping"),
            "_assign_groups",
            lambda **kwargs: dict.fromkeys(kwargs["arg_ids"], "g1"),
        )
        step_config = {"predefined_groups": ["交通"]}
    else:
        step_config = {"cluster_nums": [3, 6], "save_umap_model": False}
    config = {"input": "source", "question": "q", "analysis_mode": mode, "provider": "local", step: step_config}

    def run(name, seed):
        step_config["random_seed"] = seed
        config_path = tmp_path / f"{name}.json"
        config_path.write_text(json.dumps(config))
        monkeypatch.setattr(
            sys,
            "argv",
            [
                "kouchou-analyze",
                "--config",
                str(config_path),
                "--output-dir",
                str(saved_inputs.parent),
                "--reuse-from",
                str(saved_inputs),
                "--only",
                step,
            ],
        )
        assert main() == 0
        output = saved_inputs.parent / name
        assert (output / "embeddings.pkl").read_bytes() == (saved_inputs / "embeddings.pkl").read_bytes()
        status = json.loads((output / "hierarchical_status.json").read_text())
        assert [job["step"] for job in status["completed_jobs"]] == [step]
        assert status["completed_jobs"][0]["params"]["random_seed"] == seed
        return config_path, (output / "hierarchical_clusters.csv").read_bytes()

    comparison_path, first = run("comparison", 0)
    _, same_seed = run("repeat", 0)
    _, different_seed = run("different", 1)
    assert first == same_seed
    assert first != different_seed

    for seed, expected_run in ((0, False), (1, True), (None, True)):
        step_config["random_seed"] = seed
        comparison_path.write_text(json.dumps(config))
        pipeline = PipelineOrchestrator.from_config(
            comparison_path, output_base_dir=saved_inputs.parent, validate_api_keys_early=False, persist_status=False
        )
        plan = {job["step"]: job for job in pipeline.get_plan()}
        assert plan["embedding"]["run"] is False
        assert plan[step]["run"] is expected_run
        if expected_run:
            assert "random_seed" in plan[step]["reason"]


@pytest.mark.parametrize(
    ("mode", "step"),
    [("hierarchical", "hierarchical_clustering"), ("llm_grouping", "llm_grouping")],
)
def test_direct_orchestrator_accepts_a_config_without_a_seed(saved_inputs, monkeypatch, mode, step):
    if mode == "llm_grouping":
        monkeypatch.setattr(
            import_module("analysis_core.steps.llm_grouping"),
            "_assign_groups",
            lambda **kwargs: dict.fromkeys(kwargs["arg_ids"], "g1"),
        )
        step_config = {"predefined_groups": ["交通"]}
    else:
        step_config = {"cluster_nums": [3, 6], "save_umap_model": False}
    config = normalize_config(
        {
            "input": "source",
            "question": "q",
            "analysis_mode": mode,
            "provider": "local",
            "output_dir": saved_inputs.name,
            step: step_config,
        },
        include_source_code=False,
    )
    config[step].pop("random_seed", None)
    config["plan"] = [
        {"step": spec["step"], "run": spec["step"] == step} for spec in load_specs(get_specs_path_for_mode(mode))
    ]

    result = PipelineOrchestrator(config, output_base_dir=saved_inputs.parent).run_default()

    assert result.success, result.error
    assert len(pl.read_csv(saved_inputs / "hierarchical_clusters.csv")) == 30


@pytest.mark.parametrize("bad_seed", [False, -1, 2**32, "42", 42.0])
@pytest.mark.parametrize(
    ("mode", "step"),
    [("hierarchical", "hierarchical_clustering"), ("llm_grouping", "llm_grouping")],
)
def test_rejects_invalid_clustering_seed_before_running(mode, step, bad_seed):
    specs = load_specs(get_specs_path_for_mode(mode))
    config = {"input": "source", "question": "q", "analysis_mode": mode, step: {"random_seed": bad_seed}}
    with pytest.raises(ValueError, match=rf"{step}\.random_seed"):
        validate_config(config, specs)
