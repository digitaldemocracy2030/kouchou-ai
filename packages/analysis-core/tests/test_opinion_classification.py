"""Opinion classification: prompt, parsing, ratios, output files, and pipeline wiring."""

import importlib
import json

import polars as pl
import pytest

from analysis_core.steps.opinion_labels import (
    DEFAULT_LABEL_IDS,
    DEFAULT_LABELS,
    InvalidClassificationResponse,
    OpinionLabel,
    build_classification_prompt,
    compute_label_ratios,
    parse_classification_response,
)

classification = importlib.import_module("analysis_core.steps.opinion_classification")
aggregation = importlib.import_module("analysis_core.steps.hierarchical_aggregation")


class TestPrompt:
    def test_default_prompt_contains_every_label_and_examples(self):
        prompt = build_classification_prompt()
        for label in DEFAULT_LABELS:
            assert label.id in prompt
            assert label.name in prompt
            assert label.includes in prompt
            assert label.excludes in prompt
        assert '{"hate_or_insult": false, "policy_proposal": false}' in prompt
        assert "/human" in prompt  # few-shot examples are present for the default set

    def test_custom_labels_drop_default_examples(self):
        labels = [OpinionLabel(id="question", name="質問", includes="疑問文", excludes="断定")]
        prompt = build_classification_prompt(labels)
        assert "question（質問）" in prompt
        assert "hate_or_insult" not in prompt
        assert "/human" not in prompt

    def test_empty_labels_rejected(self):
        with pytest.raises(ValueError):
            build_classification_prompt([])

    def test_registered_as_default_prompt(self):
        from analysis_core.prompts import DEFAULT_PROMPTS, get_default_prompt

        assert "opinion_classification" in DEFAULT_PROMPTS
        assert get_default_prompt("opinion_classification") == build_classification_prompt()


class TestParse:
    def test_dict_and_string_forms(self):
        expected = {"hate_or_insult": True, "policy_proposal": False}
        assert parse_classification_response(expected, DEFAULT_LABEL_IDS) == expected
        assert parse_classification_response(json.dumps(expected), DEFAULT_LABEL_IDS) == expected
        fenced = "```json\n" + json.dumps(expected) + "\n```"
        assert parse_classification_response(fenced, DEFAULT_LABEL_IDS) == expected
        chatty = "判定結果です。\n" + json.dumps(expected) + "\n以上"
        assert parse_classification_response(chatty, DEFAULT_LABEL_IDS) == expected

    def test_string_booleans_are_accepted(self):
        data = {"hate_or_insult": "true", "policy_proposal": "no"}
        assert parse_classification_response(data, DEFAULT_LABEL_IDS) == {
            "hate_or_insult": True,
            "policy_proposal": False,
        }

    def test_extra_keys_ignored(self):
        data = {"hate_or_insult": False, "policy_proposal": True, "reason": "x"}
        assert parse_classification_response(data, DEFAULT_LABEL_IDS) == {
            "hate_or_insult": False,
            "policy_proposal": True,
        }

    @pytest.mark.parametrize(
        "response",
        [
            "not json at all",
            "[]",
            {"hate_or_insult": True},
            {"hate_or_insult": "maybe", "policy_proposal": False},
            {"hate_or_insult": 1.5, "policy_proposal": False},
            42,
        ],
    )
    def test_malformed_responses_are_errors_not_results(self, response):
        with pytest.raises(InvalidClassificationResponse):
            parse_classification_response(response, DEFAULT_LABEL_IDS)


class TestRatios:
    def test_counts_and_ratios(self):
        rows = [
            {"hate_or_insult": True, "policy_proposal": False},
            {"hate_or_insult": False, "policy_proposal": True},
            {"hate_or_insult": True, "policy_proposal": True},
            {"hate_or_insult": False, "policy_proposal": False},
        ]
        summary = compute_label_ratios(rows, DEFAULT_LABEL_IDS)
        assert summary["total"] == 4
        assert summary["labels"]["hate_or_insult"] == {"count": 2, "ratio": 0.5}
        assert summary["labels"]["policy_proposal"] == {"count": 2, "ratio": 0.5}

    def test_accepts_csv_strings_and_empty_input(self):
        rows = [{"hate_or_insult": "yes", "policy_proposal": "no"}, {"hate_or_insult": "no", "policy_proposal": "no"}]
        summary = compute_label_ratios(rows, DEFAULT_LABEL_IDS)
        assert summary["labels"]["hate_or_insult"] == {"count": 1, "ratio": 0.5}
        assert summary["labels"]["policy_proposal"] == {"count": 0, "ratio": 0.0}
        assert compute_label_ratios([], DEFAULT_LABEL_IDS)["labels"]["hate_or_insult"] == {"count": 0, "ratio": 0.0}


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
        "opinion_classification": {"model": "m", "prompt": "p", "workers": 2},
    }
    config["opinion_classification"].update(overrides)
    return config


class TestStep:
    def test_writes_csv_summary_and_usage(self, tmp_path, monkeypatch):
        out = _write_args(tmp_path, ["バスを増やしてほしい", "あいつは無能だ", "今日は晴れ"])
        answers = {
            "バスを増やしてほしい": {"hate_or_insult": False, "policy_proposal": True},
            "あいつは無能だ": {"hate_or_insult": True, "policy_proposal": False},
            "今日は晴れ": {"hate_or_insult": False, "policy_proposal": False},
        }
        seen = []

        def fake_request(**kwargs):
            seen.append(kwargs)
            text = kwargs["messages"][1]["content"]
            return json.dumps(answers[text]), 2, 1, 3

        monkeypatch.setattr(classification, "request_to_chat_ai", fake_request)
        monkeypatch.setattr(classification, "update_progress", lambda *args, **kwargs: None)
        config = _config(tmp_path)

        classification.opinion_classification(config)

        frame = pl.read_csv(out / "opinion_classifications.csv", infer_schema_length=0)
        assert frame.columns == ["arg-id", "hate_or_insult", "policy_proposal"]
        assert frame["arg-id"].to_list() == ["A0_0", "A1_0", "A2_0"]
        assert frame["hate_or_insult"].to_list() == ["no", "yes", "no"]
        assert frame["policy_proposal"].to_list() == ["yes", "no", "no"]

        summary = json.loads((out / "opinion_classification_summary.json").read_text(encoding="utf-8"))
        assert summary["total"] == 3
        assert summary["labels"]["hate_or_insult"]["count"] == 1
        assert summary["labels"]["policy_proposal"]["ratio"] == pytest.approx(1 / 3)
        assert summary["model"] == "m" and summary["provider"] == "local"
        assert "検証" in summary["note"]

        assert config["total_token_usage"] == 9
        assert config["token_usage_input"] == 6
        assert config["token_usage_output"] == 3
        assert all(call["provider"] == "local" and call["model"] == "m" for call in seen)
        assert all(call["messages"][0]["content"] == "p" for call in seen)
        schema = seen[0]["json_schema"].model_json_schema()
        assert set(schema["required"]) == set(DEFAULT_LABEL_IDS)

    def test_custom_label_ids(self, tmp_path, monkeypatch):
        out = _write_args(tmp_path, ["a", "b"])
        monkeypatch.setattr(classification, "request_to_chat_ai", lambda **kwargs: ('{"question": true}', 1, 1, 2))
        monkeypatch.setattr(classification, "update_progress", lambda *args, **kwargs: None)
        classification.opinion_classification(_config(tmp_path, labels=["question"]))
        frame = pl.read_csv(out / "opinion_classifications.csv", infer_schema_length=0)
        assert frame.columns == ["arg-id", "question"]
        assert frame["question"].to_list() == ["yes", "yes"]

    def test_failure_stops_without_partial_output(self, tmp_path, monkeypatch):
        out = _write_args(tmp_path, ["fine", "private broken", "also fine"])

        def fake_request(**kwargs):
            text = kwargs["messages"][1]["content"]
            if text == "private broken":
                return "not json", 1, 1, 2
            return '{"hate_or_insult": false, "policy_proposal": false}', 1, 1, 2

        monkeypatch.setattr(classification, "request_to_chat_ai", fake_request)
        monkeypatch.setattr(classification, "update_progress", lambda *args, **kwargs: None)
        with pytest.raises(classification.ClassificationBatchError, match="1件") as error:
            classification.opinion_classification(_config(tmp_path))
        assert error.value.failures == {"A1_0": "invalid_response"}
        assert "private" not in str(error.value)
        assert not (out / "opinion_classifications.csv").exists()
        assert not (out / "opinion_classification_summary.json").exists()

    def test_exception_type_is_reported(self, tmp_path, monkeypatch):
        _write_args(tmp_path, ["x"])

        def fake_request(**kwargs):
            raise RuntimeError("private API failure")

        monkeypatch.setattr(classification, "request_to_chat_ai", fake_request)
        monkeypatch.setattr(classification, "update_progress", lambda *args, **kwargs: None)
        with pytest.raises(classification.ClassificationBatchError) as error:
            classification.opinion_classification(_config(tmp_path))
        assert error.value.failures == {"A0_0": "RuntimeError"}
        assert "private" not in str(error.value)


class TestAggregationMerge:
    def _arguments(self):
        return [
            {"arg_id": "A1_0", "argument": "x", "attributes": None},
            {"arg_id": "A2_0", "argument": "y", "attributes": {"channel": "ch1"}},
            {"arg_id": "A3_0", "argument": "z", "attributes": None},
        ]

    def test_labels_are_added_to_attributes(self, tmp_path):
        path = tmp_path / "opinion_classifications.csv"
        pl.DataFrame(
            {"arg-id": ["A1_0", "A2_0"], "hate_or_insult": ["no", "yes"], "policy_proposal": ["yes", "no"]}
        ).write_csv(path)
        arguments = self._arguments()
        assert aggregation._merge_opinion_classifications(arguments, str(path)) == 2
        assert arguments[0]["attributes"] == {"hate_or_insult": "no", "policy_proposal": "yes"}
        assert arguments[1]["attributes"] == {"channel": "ch1", "hate_or_insult": "yes", "policy_proposal": "no"}
        assert arguments[2]["attributes"] is None  # unlabelled opinions are left untouched, not dropped

    def test_missing_file_is_a_noop(self, tmp_path):
        arguments = self._arguments()
        assert aggregation._merge_opinion_classifications(arguments, str(tmp_path / "none.csv")) == 0
        assert arguments == self._arguments()


class TestPipelineWiring:
    def test_plan_disabled_by_default_and_enabled_on_request(self, tmp_path):
        from analysis_core.core import decide_what_to_run, load_specs
        from analysis_core.core.orchestration import _PACKAGE_DIR

        specs = load_specs(_PACKAGE_DIR / "specs" / "hierarchical_specs.json")
        config = {"input": "test", "question": "Test?", "output_dir": "test"}
        plan = {s["step"]: s for s in decide_what_to_run(config, None, specs, tmp_path)}
        assert plan["opinion_classification"]["run"] is False
        assert "disabled" in plan["opinion_classification"]["reason"]

        config["opinion_classification"] = {"enabled": True}
        plan = {s["step"]: s for s in decide_what_to_run(config, None, specs, tmp_path)}
        assert plan["opinion_classification"]["run"] is True

        config["force"] = True
        config["opinion_classification"] = {"enabled": False}
        plan = {s["step"]: s for s in decide_what_to_run(config, None, specs, tmp_path)}
        assert plan["opinion_classification"]["run"] is False

    def test_condition_supports_nested_config_path(self):
        from analysis_core.workflow.resolver import evaluate_condition

        condition = "${config.opinion_classification.enabled}"
        assert evaluate_condition(condition, {}, {}) is False
        assert evaluate_condition(condition, {"opinion_classification": {}}, {}) is False
        assert evaluate_condition(condition, {"opinion_classification": {"enabled": False}}, {}) is False
        assert evaluate_condition(condition, {"opinion_classification": {"enabled": True}}, {}) is True
        assert evaluate_condition("${config.flag}", {"flag": True}, {}) is True

    def test_workflow_and_registry_include_step(self):
        from analysis_core.plugin import get_registry
        from analysis_core.workflows.hierarchical_default import create_hierarchical_workflow

        workflow = create_hierarchical_workflow()
        step = workflow.get_step("opinion_classification")
        assert step is not None
        assert step.plugin == "analysis.opinion_classification"
        assert step.optional is True
        assert "opinion_classification" in workflow.get_step("aggregation").depends_on

        registry = get_registry()
        registry.register_builtin_plugins()
        plugin = registry.get("analysis.opinion_classification")
        assert plugin.metadata.inputs == ["arguments"]
        assert plugin.metadata.use_llm is True

    def test_normalize_config_defaults(self):
        from analysis_core.compat import normalize_config

        normalized = normalize_config({"model": "gpt-x"}, include_source_code=False)
        step = normalized["opinion_classification"]
        assert step["enabled"] is False
        assert step["model"] == "gpt-x"
        assert "hate_or_insult" in step["prompt"]

    def test_plugin_fills_prompt_and_model_from_context(self, tmp_path, monkeypatch):
        from analysis_core.plugin import StepContext, StepInputs
        from analysis_core.plugins.builtin.opinion_classification import opinion_classification_plugin

        output_dir = tmp_path / "out" / "demo"
        output_dir.mkdir(parents=True)
        seen = {}

        def fake_impl(config):
            seen.update(config)
            config["total_token_usage"] = 5
            (output_dir / "opinion_classifications.csv").write_text("arg-id,hate_or_insult\n", encoding="utf-8")

        monkeypatch.setattr(classification, "opinion_classification", fake_impl)
        ctx = StepContext(
            output_dir=output_dir,
            input_dir=tmp_path / "in",
            dataset="demo",
            provider="local",
            model="ctx-model",
            local_llm_address="127.0.0.1:11434",
        )
        outputs = opinion_classification_plugin.run(ctx, StepInputs(), {"opinion_classification": {"workers": 3}})

        assert seen["provider"] == "local"
        assert seen["local_llm_address"] == "127.0.0.1:11434"
        assert seen["opinion_classification"]["model"] == "ctx-model"
        assert seen["opinion_classification"]["workers"] == 3
        assert "hate_or_insult" in seen["opinion_classification"]["prompt"]
        assert outputs.artifacts["classifications"] == output_dir / "opinion_classifications.csv"
        assert outputs.token_usage == 5


def test_classify_batch_keeps_slow_success_beyond_request_timeout(monkeypatch):
    """1 リクエストの上限は SDK の timeout に任せ、遅れて成功した応答を TimeoutError にしない。"""
    import time

    def classify(text, *args):
        if text == "slow":
            time.sleep(0.3)
        return {"hate_or_insult": False}, 2, 1, 3

    monkeypatch.setattr(classification, "classify_argument", classify)
    config: dict = {}
    rows = classification.classify_batch(
        ["a1", "a2"], ["fast", "slow"], "p", ("hate_or_insult",), "m", 2, config=config, timeout_seconds=0.05
    )
    assert rows == [{"hate_or_insult": False}, {"hate_or_insult": False}]
    assert config["total_token_usage"] == 6
