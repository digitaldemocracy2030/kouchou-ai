"""User-defined labels for opinion classification (#1225)."""

import importlib
import json

import polars as pl
import pytest

from analysis_core.core import load_specs
from analysis_core.core.orchestration import _PACKAGE_DIR, validate_config
from analysis_core.steps.opinion_labels import (
    DEFAULT_CLASSIFICATION_PROMPT,
    DEFAULT_LABEL_IDS,
    DEFAULT_LABELS,
    InvalidLabelSpec,
    resolve_classification_prompt,
    resolve_label_spec,
)

classification = importlib.import_module("analysis_core.steps.opinion_classification")

SAFETY = {
    "id": "safety_concern",
    "name": "安全上確認すべき指摘",
    "includes": "設備・避難経路・手順について、事故や危険につながりうる点を指摘しているもの",
    "excludes": "一般的な感想",
}


class TestResolveLabelSpec:
    @pytest.mark.parametrize("spec", [None, []])
    def test_missing_or_empty_means_builtin_labels(self, spec):
        assert resolve_label_spec(spec) == (DEFAULT_LABEL_IDS, DEFAULT_LABELS)

    def test_mixes_builtin_ids_and_user_definitions_in_order(self):
        ids, definitions = resolve_label_spec([SAFETY, "policy_proposal"])
        assert ids == ("safety_concern", "policy_proposal")
        assert definitions[0].name == "安全上確認すべき指摘"
        assert definitions[0].excludes == "一般的な感想"
        assert definitions[1] == DEFAULT_LABELS[1]

    def test_excludes_is_optional_and_values_are_trimmed(self):
        ids, definitions = resolve_label_spec([{"id": " problem ", "name": " 業務の課題 ", "includes": " 困りごと "}])
        assert ids == ("problem",)
        assert (definitions[0].name, definitions[0].includes, definitions[0].excludes) == ("業務の課題", "困りごと", "")

    def test_unknown_string_id_has_no_definition(self):
        # これまでどおり、定義を含むプロンプトを自分で書けば任意の ID を使える
        ids, definitions = resolve_label_spec(["question"])
        assert ids == ("question",) and definitions == (None,)

    def test_builtin_id_can_be_redefined(self):
        _, definitions = resolve_label_spec([{"id": "policy_proposal", "name": "提案", "includes": "提案しているもの"}])
        assert definitions[0].includes == "提案しているもの"

    @pytest.mark.parametrize(
        ("spec", "message"),
        [
            ("safety_concern", "リスト"),
            ({"id": "x"}, "リスト"),
            ([{"id": "x", "name": "n"}], "includes"),
            ([{"id": "x", "name": "n", "includes": "  "}], "includes"),
            ([{"id": "x", "name": "n", "includes": "i", "description": "d"}], "使えない項目"),
            ([{"id": "x", "name": 1, "includes": "i"}], "文字列"),
            ([3], "オブジェクト"),
            (["安全"], "使えません"),
            (["1st"], "使えません"),
            (["arg-id"], "使えません"),
            (["stance_score"], "他のステップ"),
            (["novelty_score"], "他のステップ"),
            (["policy_proposal", {"id": "policy_proposal", "name": "n", "includes": "i"}], "重複"),
        ],
    )
    def test_invalid_specs_are_rejected(self, spec, message):
        with pytest.raises(InvalidLabelSpec, match=message):
            resolve_label_spec(spec)


class TestResolvePrompt:
    def test_prompt_written_by_user_is_kept(self):
        ids, definitions = resolve_label_spec(["question"])
        assert resolve_classification_prompt("my prompt", ids, definitions) == "my prompt"

    @pytest.mark.parametrize("prompt", [None, "", DEFAULT_CLASSIFICATION_PROMPT, DEFAULT_CLASSIFICATION_PROMPT + "\n"])
    def test_builtin_or_missing_prompt_is_rebuilt_from_definitions(self, prompt):
        ids, definitions = resolve_label_spec([SAFETY, "policy_proposal"])
        built = resolve_classification_prompt(prompt, ids, definitions)
        assert "safety_concern（安全上確認すべき指摘）" in built
        assert SAFETY["includes"] in built and SAFETY["excludes"] in built
        assert "policy_proposal（政策・制度への提案）" in built
        assert "hate_or_insult" not in built
        assert "/human" not in built  # 既定の 2 ラベル前提の入出力例は出さない

    def test_builtin_labels_keep_the_builtin_prompt(self):
        ids, definitions = resolve_label_spec(None)
        assert resolve_classification_prompt(DEFAULT_CLASSIFICATION_PROMPT, ids, definitions) == (
            DEFAULT_CLASSIFICATION_PROMPT
        )

    def test_subset_of_builtin_labels_describes_only_that_label(self):
        ids, definitions = resolve_label_spec(["policy_proposal"])
        built = resolve_classification_prompt(DEFAULT_CLASSIFICATION_PROMPT, ids, definitions)
        assert "policy_proposal" in built and "hate_or_insult" not in built

    def test_label_without_definition_needs_a_user_prompt(self):
        ids, definitions = resolve_label_spec([SAFETY, "question"])
        with pytest.raises(InvalidLabelSpec, match="question"):
            resolve_classification_prompt(None, ids, definitions)

    def test_empty_excludes_line_is_omitted(self):
        ids, definitions = resolve_label_spec([{"id": "problem", "name": "課題", "includes": "困りごと"}])
        built = resolve_classification_prompt(None, ids, definitions)
        assert "## problem（課題）\n- 該当: 困りごと\n\n" in built
        assert "非該当: \n" not in built


class TestStepWithUserDefinedLabels:
    def test_sends_built_prompt_and_records_definitions(self, tmp_path, monkeypatch):
        out = tmp_path / "report"
        out.mkdir()
        pl.DataFrame({"arg-id": ["A0_0", "A1_0"], "argument": ["非常口が塞がっていた", "楽しかった"]}).write_csv(
            out / "args.csv"
        )
        answers = {
            "非常口が塞がっていた": {"safety_concern": True, "problem": True},
            "楽しかった": {"safety_concern": False, "problem": False},
        }
        seen = []

        def fake_request(**kwargs):
            seen.append(kwargs)
            return json.dumps(answers[kwargs["messages"][1]["content"]]), 1, 1, 2

        monkeypatch.setattr(classification, "request_to_chat_ai", fake_request)
        monkeypatch.setattr(classification, "update_progress", lambda *args, **kwargs: None)
        config = {
            "output_dir": "report",
            "_output_base_dir": str(tmp_path),
            "provider": "local",
            "opinion_classification": {
                "model": "m",
                # 設定に prompt が無いときは既定のプロンプトが入った状態でステップに来る
                "prompt": DEFAULT_CLASSIFICATION_PROMPT,
                "workers": 1,
                "labels": [SAFETY, {"id": "problem", "name": "業務の課題", "includes": "困っていること"}],
            },
        }

        classification.opinion_classification(config)

        system_prompt = seen[0]["messages"][0]["content"]
        assert "safety_concern（安全上確認すべき指摘）" in system_prompt
        assert "problem（業務の課題）" in system_prompt
        assert "hate_or_insult" not in system_prompt
        assert set(seen[0]["json_schema"].model_json_schema()["required"]) == {"safety_concern", "problem"}

        frame = pl.read_csv(out / "opinion_classifications.csv", infer_schema_length=0)
        assert frame.columns == ["arg-id", "safety_concern", "problem"]
        assert frame["safety_concern"].to_list() == ["yes", "no"]

        summary = json.loads((out / "opinion_classification_summary.json").read_text(encoding="utf-8"))
        assert summary["labels"]["safety_concern"] == {"count": 1, "ratio": 0.5}
        assert [d["id"] for d in summary["label_definitions"]] == ["safety_concern", "problem"]
        assert summary["label_definitions"][0]["includes"] == SAFETY["includes"]

    def test_invalid_labels_stop_before_any_request(self, tmp_path, monkeypatch):
        out = tmp_path / "report"
        out.mkdir()
        pl.DataFrame({"arg-id": ["A0_0"], "argument": ["x"]}).write_csv(out / "args.csv")
        monkeypatch.setattr(classification, "request_to_chat_ai", lambda **kwargs: pytest.fail("LLM was called"))
        config = {
            "output_dir": "report",
            "_output_base_dir": str(tmp_path),
            "provider": "local",
            "opinion_classification": {"model": "m", "prompt": DEFAULT_CLASSIFICATION_PROMPT, "labels": ["question"]},
        }
        with pytest.raises(InvalidLabelSpec):
            classification.opinion_classification(config)


SPECS = load_specs(_PACKAGE_DIR / "specs" / "hierarchical_specs.json")


class TestValidateConfig:
    def _config(self, **step):
        return {"input": "i", "question": "q", "opinion_classification": {"enabled": True, **step}}

    def test_user_defined_labels_pass(self):
        validate_config(self._config(labels=[SAFETY, "policy_proposal"]), SPECS)

    def test_bad_label_spec_fails_before_extraction(self):
        with pytest.raises(Exception, match="重複"):
            validate_config(self._config(labels=["policy_proposal", "policy_proposal"]), SPECS)

    def test_label_without_definition_needs_prompt(self):
        with pytest.raises(Exception, match="定義がありません"):
            validate_config(self._config(labels=["question"]), SPECS)
        validate_config(self._config(labels=["question"], prompt="自分で書いた定義つきのプロンプト"), SPECS)

    def test_disabled_step_is_not_checked(self):
        validate_config(
            {"input": "i", "question": "q", "opinion_classification": {"enabled": False, "labels": "x"}}, SPECS
        )
