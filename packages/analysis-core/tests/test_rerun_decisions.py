"""Regression tests for rerun decisions and CLI options (--only / --dry-run / --reuse-from)."""

import json

import pytest

from analysis_core.core import decide_what_to_run, initialization, load_specs, update_status
from analysis_core.core.orchestration import _PACKAGE_DIR
from analysis_core.prompts import get_default_prompt

HIERARCHICAL_SPECS = _PACKAGE_DIR / "specs" / "hierarchical_specs.json"
LLM_GROUPING_SPECS = _PACKAGE_DIR / "specs" / "llm_grouping_specs.json"


def _initialized_config(tmp_path, specs_path=HIERARCHICAL_SPECS, **overrides):
    """Build a fully-defaulted config the same way the CLI does."""
    config_path = tmp_path / "job.json"
    base = {"input": "comments", "question": "Q?", "provider": "local"}
    if specs_path == LLM_GROUPING_SPECS:
        base["analysis_mode"] = "llm_grouping"
    config_path.write_text(json.dumps(base), encoding="utf-8")
    config = initialization(
        config_path=config_path,
        skip_interaction=True,
        persist_status=False,
        output_base_dir=tmp_path / "outputs",
        input_base_dir=tmp_path / "inputs",
    )
    for key, value in overrides.items():
        if isinstance(value, dict) and isinstance(config.get(key), dict):
            config[key] = {**config[key], **value}
        else:
            config[key] = value
    return config


def _completed_status(config, specs, completed="2026-01-01T00:00:00"):
    """Status of a previous run that completed every step with the given config."""
    return {
        "status": "completed",
        "completed_jobs": [
            {
                "step": spec["step"],
                "completed": completed,
                "params": dict(config[spec["step"]]),
                "global_params": {
                    k: config.get(k)
                    for k in (
                        "input",
                        "question",
                        "intro",
                        "is_pubcom",
                        "enable_source_link",
                        "enable_original_comments",
                    )
                },
            }
            for spec in specs
        ],
        "previously_completed_jobs": [],
    }


def _touch_artifacts(tmp_path, config, specs):
    out = tmp_path / "outputs" / config["output_dir"]
    out.mkdir(parents=True, exist_ok=True)
    for spec in specs:
        for filename in [spec["filename"], *spec.get("extra_files", [])]:
            (out / filename).write_text("x", encoding="utf-8")


def _plan_with_previous(tmp_path, config, previous, specs):
    config = {**config, "previous": previous}
    return {p["step"]: p for p in decide_what_to_run(config, previous, specs, tmp_path / "outputs")}


class TestParamChangesAreDetected:
    """#6: input / question / intro / properties / hidden_properties changes must trigger a rerun."""

    @pytest.mark.parametrize(
        ("override", "expected_step"),
        [
            ({"input": "other_comments"}, "extraction"),
            ({"extraction": {"properties": ["age"]}}, "extraction"),
            ({"hierarchical_aggregation": {"hidden_properties": {"age": ["10"]}}}, "hierarchical_aggregation"),
            ({"hierarchical_aggregation": {"sampling_num": 10}}, "hierarchical_aggregation"),
            ({"question": "Another?"}, "hierarchical_aggregation"),
            ({"intro": "new intro"}, "hierarchical_aggregation"),
            ({"is_pubcom": True}, "hierarchical_aggregation"),
            ({"enable_source_link": True}, "hierarchical_aggregation"),
            ({"enable_original_comments": True}, "hierarchical_aggregation"),
        ],
    )
    def test_hierarchical_param_change_reruns_step(self, tmp_path, override, expected_step):
        config = _initialized_config(tmp_path)
        specs = load_specs(HIERARCHICAL_SPECS)
        previous = _completed_status(config, specs)
        _touch_artifacts(tmp_path, config, specs)

        unchanged = _plan_with_previous(tmp_path, config, previous, specs)
        assert unchanged[expected_step]["run"] is False

        changed_config = _initialized_config(tmp_path, **override)
        plan = _plan_with_previous(tmp_path, changed_config, previous, specs)
        assert plan[expected_step]["run"] is True
        assert plan["hierarchical_aggregation"]["run"] is True

    def test_llm_grouping_question_change_reruns_grouping(self, tmp_path):
        config = _initialized_config(tmp_path, specs_path=LLM_GROUPING_SPECS)
        specs = load_specs(LLM_GROUPING_SPECS)
        previous = _completed_status(config, specs)
        _touch_artifacts(tmp_path, config, specs)

        changed_config = _initialized_config(tmp_path, specs_path=LLM_GROUPING_SPECS, question="Another?")
        plan = _plan_with_previous(tmp_path, changed_config, previous, specs)
        assert plan["extraction"]["run"] is False
        assert plan["llm_grouping"]["run"] is True

    def test_records_without_global_params_do_not_force_rerun(self, tmp_path):
        """Status files written before global_params existed keep skipping unchanged steps."""
        config = _initialized_config(tmp_path)
        specs = load_specs(HIERARCHICAL_SPECS)
        previous = _completed_status(config, specs)
        for job in previous["completed_jobs"]:
            del job["global_params"]
        _touch_artifacts(tmp_path, config, specs)

        plan = _plan_with_previous(tmp_path, config, previous, specs)
        assert all(not p["run"] for p in plan.values())

    def test_reuse_from_does_not_seed_aggregation_or_visualization(self, tmp_path):
        config = _initialized_config(tmp_path)
        specs = load_specs(HIERARCHICAL_SPECS)
        source_dir = tmp_path / "outputs" / "source_job"
        source_dir.mkdir(parents=True)
        for spec in specs:
            if spec["filename"] == "report":
                (source_dir / "report").mkdir()
                (source_dir / "report" / "index.html").write_text("<html></html>", encoding="utf-8")
            else:
                (source_dir / spec["filename"]).write_text("x", encoding="utf-8")
        (source_dir / "relations.csv").write_text("x", encoding="utf-8")
        (source_dir / "hierarchical_status.json").write_text(
            json.dumps(_completed_status(config, specs)), encoding="utf-8"
        )

        config_path = tmp_path / "compare_job.json"
        config_path.write_text(json.dumps({"input": "other", "question": "Q?", "provider": "local"}), encoding="utf-8")
        new_config = initialization(
            config_path=config_path,
            skip_interaction=True,
            output_base_dir=tmp_path / "outputs",
            input_base_dir=tmp_path / "inputs",
            reuse_from="source_job",
        )

        dest = tmp_path / "outputs" / "compare_job"
        assert (dest / "hierarchical_overview.txt").exists()
        assert not (dest / "hierarchical_result.json").exists()
        assert not (dest / "report").exists()
        plan = {p["step"]: p for p in new_config["plan"]}
        assert plan["hierarchical_aggregation"]["run"] is True

    def test_run_workflow_records_global_params(self, tmp_path, monkeypatch):
        from analysis_core import PipelineOrchestrator
        from analysis_core.plugin import StepOutputs
        from analysis_core.workflow.definition import StepResult as WorkflowStepResult
        from analysis_core.workflow.definition import WorkflowResult

        orchestrator = PipelineOrchestrator.from_dict(
            config={"name": "demo", "input": "demo", "question": "Test?", "provider": "local", "model": "dummy"},
            output_dir="demo",
            output_base_dir=tmp_path / "outputs",
            input_base_dir=tmp_path / "inputs",
        )

        class FakeEngine:
            def run(self, workflow, config, ctx, on_step_start=None, on_step_complete=None, skip_steps=None):
                result = WorkflowResult(workflow_id="test")
                step_result = WorkflowStepResult(step_id="extraction", success=True, outputs=StepOutputs())
                on_step_complete("extraction", step_result)
                result.step_results["extraction"] = step_result
                return result

        monkeypatch.setattr("analysis_core.workflow.WorkflowEngine", FakeEngine)
        orchestrator.run_workflow()

        status = json.loads((tmp_path / "outputs" / "demo" / "hierarchical_status.json").read_text(encoding="utf-8"))
        job = status["completed_jobs"][0]
        assert job["global_params"]["input"] == "demo"
        assert job["global_params"]["question"] == "Test?"


class TestStaleDownstreamAfterFailure:
    """#7: a downstream step older than its upstream must re-run even if params are unchanged."""

    def test_downstream_older_than_upstream_reruns(self, tmp_path):
        config = _initialized_config(tmp_path)
        specs = load_specs(HIERARCHICAL_SPECS)
        previous = _completed_status(config, specs, completed="2026-01-01T00:00:00")
        # A later run re-ran extraction with new params, then failed at embedding.
        previous["previously_completed_jobs"] = [j for j in previous["completed_jobs"] if j["step"] != "extraction"]
        previous["completed_jobs"] = [
            {**j, "completed": "2026-02-01T00:00:00"} for j in previous["completed_jobs"] if j["step"] == "extraction"
        ]
        previous["status"] = "error"
        _touch_artifacts(tmp_path, config, specs)

        plan = _plan_with_previous(tmp_path, config, previous, specs)
        assert plan["extraction"]["run"] is False
        assert plan["embedding"]["run"] is True
        assert "extraction" in plan["embedding"]["reason"]
        assert plan["hierarchical_clustering"]["run"] is True
        assert plan["hierarchical_aggregation"]["run"] is True


class TestInterruptedRunHistory:
    """#15: the latest completed records (including those of an interrupted run) win."""

    def test_interrupted_run_records_take_precedence(self, tmp_path):
        config = _initialized_config(tmp_path)
        specs = load_specs(HIERARCHICAL_SPECS)
        finished = _completed_status(config, specs, completed="2026-01-01T00:00:00")
        interrupted_extraction = {
            "step": "extraction",
            "completed": "2026-02-01T00:00:00",
            "params": {**config["extraction"], "limit": 5},
        }
        # Status file shape left behind by an interrupted run (older versions nest "previous").
        previous = {"status": "running", "completed_jobs": [interrupted_extraction], "previous": finished}
        _touch_artifacts(tmp_path, config, specs)

        plan = _plan_with_previous(tmp_path, config, previous, specs)
        assert plan["extraction"]["run"] is True
        assert "limit" in plan["extraction"]["reason"]

    def test_status_file_does_not_nest_previous_and_keeps_history(self, tmp_path):
        config = _initialized_config(tmp_path)
        specs = load_specs(HIERARCHICAL_SPECS)
        out = tmp_path / "outputs" / config["output_dir"]
        out.mkdir(parents=True, exist_ok=True)
        (out / "hierarchical_status.json").write_text(json.dumps(_completed_status(config, specs)), encoding="utf-8")

        config_path = tmp_path / "job.json"
        rerun = initialization(
            config_path=config_path,
            skip_interaction=True,
            output_base_dir=tmp_path / "outputs",
            input_base_dir=tmp_path / "inputs",
        )
        assert "previous" in rerun
        status = json.loads((out / "hierarchical_status.json").read_text(encoding="utf-8"))
        assert "previous" not in status
        assert {j["step"] for j in status["previously_completed_jobs"]} == {s["step"] for s in specs}

    def test_run_workflow_marks_status_on_keyboard_interrupt(self, tmp_path, monkeypatch):
        from analysis_core import PipelineOrchestrator

        out = tmp_path / "outputs" / "demo"
        out.mkdir(parents=True)
        (out / "hierarchical_status.json").write_text(
            json.dumps({"completed_jobs": [{"step": "extraction", "params": {}}]}), encoding="utf-8"
        )
        orchestrator = PipelineOrchestrator.from_dict(
            config={"name": "demo", "input": "demo", "question": "Test?", "provider": "local", "model": "dummy"},
            output_dir="demo",
            output_base_dir=tmp_path / "outputs",
            input_base_dir=tmp_path / "inputs",
        )

        class FakeEngine:
            def run(self, workflow, config, ctx, on_step_start=None, on_step_complete=None, skip_steps=None):
                on_step_start("embedding")
                raise KeyboardInterrupt

        monkeypatch.setattr("analysis_core.workflow.WorkflowEngine", FakeEngine)
        with pytest.raises(KeyboardInterrupt):
            orchestrator.run_workflow()

        status = json.loads((out / "hierarchical_status.json").read_text(encoding="utf-8"))
        assert status["status"] == "error"
        assert "KeyboardInterrupt" in status["error"]
        assert any(j["step"] == "extraction" for j in status["previously_completed_jobs"])


class TestAtomicStatusWrite:
    """#22: a crash in the middle of writing must not leave a truncated status file."""

    def test_update_status_keeps_old_file_when_write_fails(self, tmp_path, monkeypatch):
        out = tmp_path / "job"
        out.mkdir()
        status_file = out / "hierarchical_status.json"
        status_file.write_text(json.dumps({"status": "running", "current_job": "extraction"}), encoding="utf-8")

        def broken_dump(obj, fp, **kwargs):
            fp.write('{"status": "run')
            raise OSError("disk full")

        monkeypatch.setattr("analysis_core.core.orchestration.json.dump", broken_dump)
        with pytest.raises(OSError):
            update_status({"output_dir": "job"}, {"current_job": "embedding"}, tmp_path)

        assert json.loads(status_file.read_text(encoding="utf-8"))["current_job"] == "extraction"
        assert [p.name for p in out.iterdir()] == ["hierarchical_status.json"]


class TestOnlyOption:
    """#31: --only must name an enabled spec step, and --force must not widen it."""

    def _config_path(self, tmp_path, **extra):
        path = tmp_path / "job.json"
        path.write_text(json.dumps({"input": "c", "question": "Q?", "provider": "local", **extra}), encoding="utf-8")
        return path

    @pytest.mark.parametrize("only", ["clustering", "extracton", "opinion_classification"])
    def test_invalid_or_disabled_only_is_rejected(self, tmp_path, only):
        with pytest.raises(ValueError, match="--only"):
            initialization(
                config_path=self._config_path(tmp_path),
                only=only,
                skip_interaction=True,
                persist_status=False,
                output_base_dir=tmp_path / "outputs",
                input_base_dir=tmp_path / "inputs",
            )

    def test_force_with_only_runs_only_that_step(self, tmp_path):
        config = initialization(
            config_path=self._config_path(tmp_path),
            force=True,
            only="embedding",
            skip_interaction=True,
            persist_status=False,
            output_base_dir=tmp_path / "outputs",
            input_base_dir=tmp_path / "inputs",
        )
        assert [p["step"] for p in config["plan"] if p["run"]] == ["embedding"]


class TestDryRunWithReuseFrom:
    """#32: persist_status=False must not copy artifacts or write a seeded status file."""

    def _make_source(self, tmp_path, name):
        source = tmp_path / "outputs" / name
        source.mkdir(parents=True)
        (source / "args.csv").write_text("arg-id,argument\nA1,x\n", encoding="utf-8")
        (source / "relations.csv").write_text("arg-id,comment-id\nA1,1\n", encoding="utf-8")
        (source / "hierarchical_status.json").write_text(
            json.dumps(
                {
                    "status": "completed",
                    "completed_jobs": [
                        {
                            "step": "extraction",
                            "params": {
                                "limit": 1000,
                                "model": "gpt-4o-mini",
                                "prompt": get_default_prompt("extraction"),
                            },
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )

    def test_dry_run_does_not_touch_destination(self, tmp_path):
        self._make_source(tmp_path, "source_job")
        config_path = tmp_path / "compare_job.json"
        config_path.write_text(json.dumps({"input": "c", "question": "Q?", "provider": "local"}), encoding="utf-8")

        config = initialization(
            config_path=config_path,
            skip_interaction=True,
            persist_status=False,
            output_base_dir=tmp_path / "outputs",
            input_base_dir=tmp_path / "inputs",
            reuse_from="source_job",
        )
        dest = tmp_path / "outputs" / "compare_job"
        assert not (dest / "hierarchical_status.json").exists()
        assert not (dest / "args.csv").exists()
        plan = {p["step"]: p for p in config["plan"]}
        assert plan["extraction"]["run"] is False
        assert plan["embedding"]["run"] is True

    def test_reuse_from_mismatch_with_existing_status_warns(self, tmp_path, capsys):
        self._make_source(tmp_path, "source_a")
        self._make_source(tmp_path, "source_b")
        config_path = tmp_path / "compare_job.json"
        config_path.write_text(json.dumps({"input": "c", "question": "Q?", "provider": "local"}), encoding="utf-8")
        kwargs = dict(
            config_path=config_path,
            skip_interaction=True,
            output_base_dir=tmp_path / "outputs",
            input_base_dir=tmp_path / "inputs",
        )
        initialization(reuse_from="source_a", persist_status=False, **kwargs)
        initialization(reuse_from="source_a", **kwargs)
        status_file = tmp_path / "outputs" / "compare_job" / "hierarchical_status.json"
        status_file.write_text(
            json.dumps({**json.loads(status_file.read_text(encoding="utf-8")), "status": "completed"}),
            encoding="utf-8",
        )
        capsys.readouterr()
        initialization(reuse_from="source_b", persist_status=False, **kwargs)
        assert "source_b" in capsys.readouterr().out


def _write_llm_grouping_outputs(out_dir):
    """Minimal artifacts of a finished llm_grouping job that the real aggregation can read."""
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "args.csv").write_text("arg-id,argument\nA1_0,aaa\nA2_0,bbb\n", encoding="utf-8")
    (out_dir / "relations.csv").write_text("arg-id,comment-id\nA1_0,1\nA2_0,2\n", encoding="utf-8")
    (out_dir / "embeddings.pkl").write_bytes(b"not read when embedding is reused")
    (out_dir / "hierarchical_clusters.csv").write_text(
        "arg-id,argument,x,y,cluster-level-1-id\nA1_0,aaa,0.0,0.0,g1\nA2_0,bbb,1.0,1.0,g2\n", encoding="utf-8"
    )
    (out_dir / "hierarchical_merge_labels.csv").write_text(
        "level,id,label,description,value,parent,density_rank_percentile\n1,g1,L1,D1,1,0,1.0\n1,g2,L2,D2,1,0,0.0\n",
        encoding="utf-8",
    )
    (out_dir / "hierarchical_overview.txt").write_text("overview", encoding="utf-8")


class TestSecondaryArtifacts:
    """Files a step writes besides its spec filename are seeded and checked like the main one."""

    def _make_llm_grouping_source(self, tmp_path):
        specs = load_specs(LLM_GROUPING_SPECS)
        source_config = _initialized_config(tmp_path, specs_path=LLM_GROUPING_SPECS)
        source_dir = tmp_path / "outputs" / "source_job"
        _write_llm_grouping_outputs(source_dir)
        (source_dir / "hierarchical_status.json").write_text(
            json.dumps(_completed_status(source_config, specs)), encoding="utf-8"
        )
        input_dir = tmp_path / "inputs"
        input_dir.mkdir()
        (input_dir / "comments.csv").write_text("comment-id,comment-body\n1,aaa\n2,bbb\n", encoding="utf-8")
        config_path = tmp_path / "compare_job.json"
        config_path.write_text(
            json.dumps({"input": "comments", "question": "Q?", "provider": "local", "analysis_mode": "llm_grouping"}),
            encoding="utf-8",
        )
        return config_path

    def test_reuse_from_seeds_llm_grouping_merge_labels(self, tmp_path):
        config_path = self._make_llm_grouping_source(tmp_path)
        kwargs = dict(
            config_path=config_path,
            skip_interaction=True,
            output_base_dir=tmp_path / "outputs",
            input_base_dir=tmp_path / "inputs",
            reuse_from="source_job",
        )

        dry_run = initialization(persist_status=False, **kwargs)
        assert {p["step"]: p["run"] for p in dry_run["plan"]}["llm_grouping"] is False

        config = initialization(**kwargs)
        assert (tmp_path / "outputs" / "compare_job" / "hierarchical_merge_labels.csv").exists()
        plan = {p["step"]: p["run"] for p in config["plan"]}
        assert plan["llm_grouping"] is False
        assert plan["hierarchical_aggregation"] is True

    def test_reused_llm_grouping_job_runs_aggregation(self, tmp_path):
        """Through the CLI path (workflow engine input checks + the real aggregation step)."""
        from analysis_core import PipelineOrchestrator

        config_path = self._make_llm_grouping_source(tmp_path)
        orchestrator = PipelineOrchestrator.from_config(
            config_path,
            output_base_dir=tmp_path / "outputs",
            input_base_dir=tmp_path / "inputs",
            reuse_from="source_job",
        )
        assert [p["step"] for p in orchestrator.get_plan() if p["run"]] == ["hierarchical_aggregation"]

        result = orchestrator.run_default()

        assert result.success, result.error
        dest = tmp_path / "outputs" / "compare_job"
        aggregated = json.loads((dest / "hierarchical_result.json").read_text(encoding="utf-8"))
        assert aggregated["config"]["output_dir"] == "compare_job"
        assert {cluster["label"] for cluster in aggregated["clusters"] if cluster["level"] == 1} == {"L1", "L2"}

    @pytest.mark.parametrize(
        ("specs_path", "step", "missing"),
        [
            (LLM_GROUPING_SPECS, "llm_grouping", "hierarchical_merge_labels.csv"),
            (HIERARCHICAL_SPECS, "extraction", "relations.csv"),
        ],
    )
    def test_missing_secondary_artifact_reruns_step(self, tmp_path, specs_path, step, missing):
        config = _initialized_config(tmp_path, specs_path=specs_path)
        specs = load_specs(specs_path)
        previous = _completed_status(config, specs)
        _touch_artifacts(tmp_path, config, specs)
        assert _plan_with_previous(tmp_path, config, previous, specs)[step]["run"] is False

        (tmp_path / "outputs" / config["output_dir"] / missing).unlink(missing_ok=True)
        plan = _plan_with_previous(tmp_path, config, previous, specs)
        assert plan[step]["run"] is True
        assert plan[step]["reason"] == "previous data not found"


class TestReuseFromInterruptedSource:
    """A source killed mid-run lists a re-run step twice; the newest record matches its artifact."""

    def test_reuse_from_uses_latest_record_of_each_step(self, tmp_path):
        specs = load_specs(HIERARCHICAL_SPECS)
        config = _initialized_config(tmp_path, hierarchical_clustering={"cluster_nums": [2, 4]})
        finished = _completed_status(config, specs, completed="2026-01-01T00:00:00")
        source_dir = tmp_path / "outputs" / "source_job"
        source_dir.mkdir(parents=True)
        for spec in specs:
            if spec["filename"] != "report":
                (source_dir / spec["filename"]).write_text("x", encoding="utf-8")
        (source_dir / "relations.csv").write_text("x", encoding="utf-8")
        (source_dir / "hierarchical_clusters.csv").write_text("clusters for [3, 6]", encoding="utf-8")
        # The re-run with [3, 6] was killed right after clustering: the status written while
        # running holds the new record in completed_jobs and the older ones next to it.
        clustering = next(job for job in finished["completed_jobs"] if job["step"] == "hierarchical_clustering")
        rerun_clustering = {
            **clustering,
            "completed": "2026-02-01T00:00:00",
            "params": {**clustering["params"], "cluster_nums": [3, 6]},
        }
        (source_dir / "hierarchical_status.json").write_text(
            json.dumps(
                {
                    "status": "running",
                    "completed_jobs": [rerun_clustering],
                    "previously_completed_jobs": finished["completed_jobs"],
                }
            ),
            encoding="utf-8",
        )

        config_path = tmp_path / "compare_job.json"
        config_path.write_text(
            json.dumps(
                {
                    "input": "comments",
                    "question": "Q?",
                    "provider": "local",
                    "hierarchical_clustering": {"cluster_nums": [2, 4]},
                }
            ),
            encoding="utf-8",
        )
        new_config = initialization(
            config_path=config_path,
            skip_interaction=True,
            output_base_dir=tmp_path / "outputs",
            input_base_dir=tmp_path / "inputs",
            reuse_from="source_job",
        )

        plan = {p["step"]: p for p in new_config["plan"]}
        assert plan["hierarchical_clustering"]["run"] is True
        assert "cluster_nums" in plan["hierarchical_clustering"]["reason"]
        assert plan["hierarchical_initial_labelling"]["run"] is True
        seeded = new_config["previous"]["completed_jobs"]
        seeded_clustering = next(job for job in seeded if job["step"] == "hierarchical_clustering")
        assert seeded_clustering["params"]["cluster_nums"] == [3, 6]
