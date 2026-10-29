"""Opinion stance score: prompt input, parsing, summary, output files, aggregation merge, and pipeline wiring."""

import importlib
import json

import polars as pl
import pytest

stance = importlib.import_module("analysis_core.steps.opinion_stance")
aggregation = importlib.import_module("analysis_core.steps.hierarchical_aggregation")


class TestParse:
    def test_dict_and_string_forms(self):
        assert stance.parse_stance_response({"applicable": True, "stance_score": 0.5}) == 0.5
        assert stance.parse_stance_response('{"applicable": true, "stance_score": -0.25}') == -0.25
        fenced = '```json\n{"applicable": true, "stance_score": 1}\n```'
        assert stance.parse_stance_response(fenced) == 1.0
        chatty = '判定結果です。\n{"applicable": "true", "stance_score": "0.3"}\n以上'
        assert stance.parse_stance_response(chatty) == pytest.approx(0.3)

    def test_not_applicable_is_none_not_zero(self):
        assert stance.parse_stance_response({"applicable": False, "stance_score": 0.0}) is None
        assert stance.parse_stance_response({"applicable": False, "stance_score": 0.8}) is None

    @pytest.mark.parametrize(
        "response",
        [
            "not json at all",
            "[]",
            '{"stance_score": 0.5}',
            '{"applicable": true}',
            '{"applicable": "maybe", "stance_score": 0.5}',
            '{"applicable": true, "stance_score": "high"}',
            '{"applicable": true, "stance_score": 1.5}',
            '{"applicable": true, "stance_score": -2}',
            '{"applicable": true, "stance_score": true}',
            '{"applicable": true, "stance_score": null}',
        ],
    )
    def test_malformed_responses_are_errors_not_results(self, response):
        with pytest.raises(stance.InvalidStanceResponse):
            stance.parse_stance_response(response)


class TestSummary:
    def test_counts_mean_and_distribution(self):
        summary = stance.build_summary([0.9, -0.9, 0.0, None, 0.3], provider="local", model="m", target="T")
        assert summary["total"] == 5
        assert summary["scored"] == 4
        assert summary["not_applicable"] == 1
        assert summary["mean"] == pytest.approx(0.075)
        assert summary["distribution"] == {
            "strongly_against": 1,
            "against": 0,
            "neutral": 1,
            "for": 1,
            "strongly_for": 1,
        }
        assert summary["target"] == "T"
        assert "検証" in summary["note"]

    def test_empty_input(self):
        summary = stance.build_summary([], provider="local", model="m", target="T")
        assert summary["mean"] is None
        assert summary["scored"] == 0


class TestTarget:
    def test_defaults_to_question(self):
        assert stance.resolve_target({"question": " Q? "}, {}) == "Q?"
        assert stance.resolve_target({"question": "Q?"}, {"target": "案A"}) == "案A"

    def test_missing_target_is_an_error(self):
        with pytest.raises(RuntimeError, match="target"):
            stance.resolve_target({}, {"target": None})

    def test_registered_as_default_prompt(self):
        from analysis_core.prompts import DEFAULT_PROMPTS, get_default_prompt

        assert "opinion_stance" in DEFAULT_PROMPTS
        assert get_default_prompt("opinion_stance") == stance.STANCE_PROMPT
        assert "stance_score" in stance.STANCE_PROMPT and "applicable" in stance.STANCE_PROMPT


def _write_args(tmp_path, texts):
    out = tmp_path / "report"
    out.mkdir()
    pl.DataFrame({"arg-id": [f"A{i}_0" for i in range(len(texts))], "argument": texts}).write_csv(out / "args.csv")
    return out


def _config(tmp_path, **overrides):
    config = {
        "output_dir": "report",
        "_output_base_dir": str(tmp_path),
        "provider": "local",
        "question": "図書館を建てるべきか",
        "opinion_stance": {"model": "m", "prompt": "p", "workers": 2},
    }
    config["opinion_stance"].update(overrides)
    return config


class TestStep:
    def test_writes_csv_summary_and_usage(self, tmp_path, monkeypatch):
        out = _write_args(tmp_path, ["ぜひ建ててほしい", "税金の無駄だ", "バスを増やして"])
        answers = {
            "ぜひ建ててほしい": {"applicable": True, "stance_score": 0.9},
            "税金の無駄だ": {"applicable": True, "stance_score": -0.8},
            "バスを増やして": {"applicable": False, "stance_score": 0.0},
        }
        seen = []

        def fake_request(**kwargs):
            seen.append(kwargs)
            user = kwargs["messages"][1]["content"]
            text = user.split("意見: ", 1)[1]
            return json.dumps(answers[text]), 2, 1, 3

        monkeypatch.setattr(stance, "request_to_chat_ai", fake_request)
        monkeypatch.setattr(stance, "update_progress", lambda *args, **kwargs: None)
        config = _config(tmp_path)

        stance.opinion_stance(config)

        frame = pl.read_csv(out / "opinion_stances.csv", infer_schema_length=0)
        assert frame.columns == ["arg-id", "stance_score"]
        assert frame["arg-id"].to_list() == ["A0_0", "A1_0", "A2_0"]
        assert frame["stance_score"].to_list() == ["0.9", "-0.8", None]  # 判定不能は空欄

        summary = json.loads((out / "opinion_stance_summary.json").read_text(encoding="utf-8"))
        assert summary["total"] == 3 and summary["scored"] == 2 and summary["not_applicable"] == 1
        assert summary["target"] == "図書館を建てるべきか"
        assert summary["model"] == "m" and summary["provider"] == "local"

        assert config["total_token_usage"] == 9
        assert all(call["messages"][0]["content"] == "p" for call in seen)
        assert all(call["messages"][1]["content"].startswith("対象: 図書館を建てるべきか\n意見: ") for call in seen)
        assert all(call["json_schema"] is stance.StanceResponse for call in seen)

    def test_explicit_target_overrides_question(self, tmp_path, monkeypatch):
        _write_args(tmp_path, ["a"])
        seen = []

        def fake_request(**kwargs):
            seen.append(kwargs["messages"][1]["content"])
            return '{"applicable": true, "stance_score": 0}', 1, 1, 2

        monkeypatch.setattr(stance, "request_to_chat_ai", fake_request)
        monkeypatch.setattr(stance, "update_progress", lambda *args, **kwargs: None)
        stance.opinion_stance(_config(tmp_path, target="駅前への移転案"))
        assert seen == ["対象: 駅前への移転案\n意見: a"]

    def test_failure_stops_without_partial_output_and_removes_previous(self, tmp_path, monkeypatch):
        out = _write_args(tmp_path, ["fine", "private broken"])
        (out / "opinion_stances.csv").write_text("arg-id,stance_score\nOLD_0,0.5\n", encoding="utf-8")
        (out / "opinion_stance_summary.json").write_text("{}", encoding="utf-8")

        def fake_request(**kwargs):
            if "private broken" in kwargs["messages"][1]["content"]:
                return '{"applicable": true, "stance_score": 7}', 1, 1, 2
            return '{"applicable": true, "stance_score": 0.1}', 1, 1, 2

        monkeypatch.setattr(stance, "request_to_chat_ai", fake_request)
        monkeypatch.setattr(stance, "update_progress", lambda *args, **kwargs: None)
        with pytest.raises(stance.StanceBatchError, match="1件") as error:
            stance.opinion_stance(_config(tmp_path))
        assert error.value.failures == {"A1_0": "invalid_response"}
        assert "private" not in str(error.value)
        assert not (out / "opinion_stances.csv").exists()
        assert not (out / "opinion_stance_summary.json").exists()

    def test_exception_type_is_reported_without_secrets(self, tmp_path, monkeypatch):
        _write_args(tmp_path, ["x"])

        def fake_request(**kwargs):
            raise RuntimeError("private API failure sk-secret")

        monkeypatch.setattr(stance, "request_to_chat_ai", fake_request)
        monkeypatch.setattr(stance, "update_progress", lambda *args, **kwargs: None)
        with pytest.raises(stance.StanceBatchError) as error:
            stance.opinion_stance(_config(tmp_path))
        assert error.value.failures == {"A0_0": "RuntimeError"}
        assert "secret" not in str(error.value)


class TestAggregationMerge:
    def _arguments(self):
        return [
            {"arg_id": "A1_0", "argument": "x", "attributes": None},
            {"arg_id": "A2_0", "argument": "y", "attributes": {"channel": "ch1"}},
            {"arg_id": "A3_0", "argument": "z", "attributes": None},
        ]

    def test_scores_are_added_as_numbers_and_blank_is_skipped(self, tmp_path):
        path = tmp_path / "opinion_stances.csv"
        path.write_text("arg-id,stance_score\nA1_0,0.9\nA2_0,\nA3_0,-0.5\n", encoding="utf-8")
        arguments = self._arguments()
        assert aggregation._merge_opinion_scores(arguments, str(path), "stance_score") == 2
        assert arguments[0]["attributes"] == {"stance_score": 0.9}
        assert arguments[1]["attributes"] == {"channel": "ch1"}  # 判定不能はそのまま（0 にしない）
        assert arguments[2]["attributes"] == {"stance_score": -0.5}
        assert isinstance(arguments[0]["attributes"]["stance_score"], float)

    def test_missing_file_or_column_is_a_noop(self, tmp_path):
        arguments = self._arguments()
        assert aggregation._merge_opinion_scores(arguments, str(tmp_path / "none.csv"), "stance_score") == 0
        other = tmp_path / "other.csv"
        other.write_text("arg-id,novelty_score\nA1_0,0.5\n", encoding="utf-8")
        assert aggregation._merge_opinion_scores(arguments, str(other), "stance_score") == 0
        assert arguments == self._arguments()


class TestPipelineWiring:
    def test_plan_disabled_by_default_and_enabled_on_request(self, tmp_path):
        from analysis_core.core import decide_what_to_run, load_specs
        from analysis_core.core.orchestration import _PACKAGE_DIR

        specs = load_specs(_PACKAGE_DIR / "specs" / "hierarchical_specs.json")
        config = {"input": "test", "question": "Test?", "output_dir": "test"}
        plan = {s["step"]: s for s in decide_what_to_run(config, None, specs, tmp_path)}
        assert plan["opinion_stance"]["run"] is False
        assert "disabled" in plan["opinion_stance"]["reason"]

        config["opinion_stance"] = {"enabled": True}
        plan = {s["step"]: s for s in decide_what_to_run(config, None, specs, tmp_path)}
        assert plan["opinion_stance"]["run"] is True

        config["force"] = True
        config["opinion_stance"] = {"enabled": False}
        plan = {s["step"]: s for s in decide_what_to_run(config, None, specs, tmp_path)}
        assert plan["opinion_stance"]["run"] is False

    def test_question_change_reruns_stance(self, tmp_path):
        """target を省略した賛否は question に依存するので、question が変わったら再実行する。"""
        from analysis_core.core import decide_what_to_run, load_specs
        from analysis_core.core.orchestration import _PACKAGE_DIR

        specs = load_specs(_PACKAGE_DIR / "specs" / "hierarchical_specs.json")
        out = tmp_path / "test"
        out.mkdir()
        for spec in specs:
            (out / spec["filename"]).write_text("", encoding="utf-8")
            for extra in spec.get("extra_files", []):
                (out / extra).write_text("", encoding="utf-8")
        previous_jobs = [
            {
                "step": spec["step"],
                "completed": "2026-01-01T00:00:00",
                "params": {"enabled": True} if spec["step"] == "opinion_stance" else {},
                "global_params": {"question": "Old?", "input": "test"},
            }
            for spec in specs
        ]
        config = {
            "input": "test",
            "question": "New?",
            "output_dir": "test",
            "opinion_stance": {"enabled": True},
            "previous": {"completed_jobs": previous_jobs},
        }
        plan = {s["step"]: s for s in decide_what_to_run(config, None, specs, tmp_path)}
        assert plan["opinion_stance"]["run"] is True
        assert "question" in plan["opinion_stance"]["reason"]

    def test_workflow_and_registry_include_step(self):
        from analysis_core.plugin import get_registry
        from analysis_core.workflows.hierarchical_default import create_hierarchical_workflow

        workflow = create_hierarchical_workflow()
        step = workflow.get_step("opinion_stance")
        assert step is not None
        assert step.plugin == "analysis.opinion_stance"
        assert step.optional is False
        assert step.condition == "${config.opinion_stance.enabled}"
        assert step.config["question"] == "${config.question}"
        assert "opinion_stance" in workflow.get_step("aggregation").depends_on

        registry = get_registry()
        registry.register_builtin_plugins()
        plugin = registry.get("analysis.opinion_stance")
        assert plugin.metadata.inputs == ["arguments"]
        assert plugin.metadata.use_llm is True

    def test_normalize_config_defaults(self):
        from analysis_core.compat import normalize_config

        normalized = normalize_config({"model": "gpt-x"}, include_source_code=False)
        step = normalized["opinion_stance"]
        assert step["enabled"] is False
        assert step["model"] == "gpt-x"
        assert step["target"] is None
        assert "stance_score" in step["prompt"]

    def test_plugin_passes_question_as_default_target(self, tmp_path, monkeypatch):
        from analysis_core.plugin import StepContext, StepInputs
        from analysis_core.plugins.builtin.opinion_stance import opinion_stance_plugin

        output_dir = tmp_path / "out" / "demo"
        output_dir.mkdir(parents=True)
        seen = {}

        def fake_impl(config):
            seen.update(config)
            config["total_token_usage"] = 5

        monkeypatch.setattr(stance, "opinion_stance", fake_impl)
        ctx = StepContext(output_dir=output_dir, input_dir=tmp_path / "in", dataset="demo", provider="local", model="m")
        outputs = opinion_stance_plugin.run(
            ctx, StepInputs(), {"opinion_stance": {"workers": 3, "question": "Q?", "target": None}}
        )
        assert seen["question"] == "Q?"
        assert seen["opinion_stance"]["model"] == "m"
        assert seen["opinion_stance"]["target"] is None
        assert "stance_score" in seen["opinion_stance"]["prompt"]
        assert outputs.artifacts["stances"] == output_dir / "opinion_stances.csv"
        assert outputs.token_usage == 5
