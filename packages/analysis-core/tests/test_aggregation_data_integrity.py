"""Aggregation must keep comment attribution intact (comment-id types, duplicates, stale files, counts)."""

import importlib
import json

import polars as pl

aggregation = importlib.import_module("analysis_core.steps.hierarchical_aggregation")


def _write_report(tmp_path, comments: str, args: list[tuple[str, str]], relations: list[tuple[str, str]]):
    inputs = tmp_path / "inputs"
    report = tmp_path / "outputs" / "report"
    inputs.mkdir(parents=True)
    report.mkdir(parents=True)
    (inputs / "input.csv").write_text(comments, encoding="utf-8")
    pl.DataFrame({"arg-id": [a for a, _ in args], "argument": [t for _, t in args]}).write_csv(report / "args.csv")
    # Written as text so that zero-padded ids stay exactly as extraction writes them.
    (report / "relations.csv").write_text(
        "arg-id,comment-id\n" + "".join(f"{a},{c}\n" for a, c in relations), encoding="utf-8"
    )
    pl.DataFrame(
        {
            "arg-id": [a for a, _ in args],
            "argument": [t for _, t in args],
            "x": [float(i) for i in range(len(args))],
            "y": [float(i) for i in range(len(args))],
            "cluster-level-1-id": ["1_0"] * len(args),
        }
    ).write_csv(report / "hierarchical_clusters.csv")
    pl.DataFrame(
        {
            "level": [1],
            "id": ["1_0"],
            "label": ["label"],
            "description": ["desc"],
            "value": [len(args)],
            "parent": ["0"],
            "density_rank_percentile": [0.5],
        }
    ).write_csv(report / "hierarchical_merge_labels.csv")
    (report / "hierarchical_overview.txt").write_text("overview", encoding="utf-8")
    config = {
        "input": "input",
        "output_dir": "report",
        "_input_base_dir": str(inputs),
        "_output_base_dir": str(tmp_path / "outputs"),
        "intro": "intro",
        "is_pubcom": False,
        "enable_source_link": True,
        "extraction": {"limit": 1000, "categories": {}},
        "hierarchical_aggregation": {"hidden_properties": {}},
    }
    return report, config


def _run(report, config):
    assert aggregation.hierarchical_aggregation(config) is True
    return json.loads((report / "hierarchical_result.json").read_text(encoding="utf-8"))


def test_zero_padded_comment_ids_keep_attributes_and_url(tmp_path):
    report, config = _write_report(
        tmp_path,
        "comment-id,comment-body,url,attribute_age\n001,first,https://example.com/1,20s\n002,second,https://example.com/2,30s\n",
        [("A001_0", "first"), ("A002_0", "second")],
        [("A001_0", "001"), ("A002_0", "002")],
    )
    result = _run(report, config)
    arguments = {arg["arg_id"]: arg for arg in result["arguments"]}
    assert arguments["A001_0"]["comment_id"] == "001"
    assert arguments["A001_0"]["attributes"] == {"age": "20s"}
    assert arguments["A001_0"]["url"] == "https://example.com/1"
    assert arguments["A002_0"]["comment_id"] == "002"
    assert arguments["A002_0"]["attributes"] == {"age": "30s"}


def test_empty_description_rewritten_by_csv_module_stays_empty(tmp_path):
    # 管理画面のラベル編集（csv.DictWriter）で書き直すと、空の description は引用符なしの空欄になる
    report, config = _write_report(tmp_path, "comment-id,comment-body\n1,body\n", [("A1_0", "body")], [("A1_0", "1")])
    (report / "hierarchical_merge_labels.csv").write_text(
        "level,id,label,description,value,parent,density_rank_percentile\n1,1_0,交通,,1,0,0.5\n", encoding="utf-8"
    )
    result = _run(report, config)
    cluster = next(c for c in result["clusters"] if c["id"] == "1_0")
    assert cluster["label"] == "交通"
    assert cluster["takeaway"] == ""


def test_identical_opinions_from_different_comments_keep_each_respondent(tmp_path, monkeypatch):
    extraction = importlib.import_module("analysis_core.steps.extraction")
    inputs = tmp_path / "inputs"
    report = tmp_path / "outputs" / "report"
    inputs.mkdir()
    report.mkdir(parents=True)
    (inputs / "input.csv").write_text(
        "comment-id,comment-body,attribute_age\nc1,賛成です,20s\nc2,賛成です。,30s\n", encoding="utf-8"
    )
    config = {
        "input": "input",
        "output_dir": "report",
        "provider": "openai",
        "_input_base_dir": str(inputs),
        "_output_base_dir": str(tmp_path / "outputs"),
        "extraction": {"model": "m", "prompt": "p", "workers": 2, "limit": 10, "properties": []},
    }
    monkeypatch.setattr(extraction, "update_progress", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        extraction, "request_to_chat_ai", lambda **kwargs: ('{"extractedOpinionList": ["賛成"]}', 1, 1, 2)
    )
    extraction.extraction(config)

    args = pl.read_csv(report / "args.csv", infer_schema_length=0)
    relations = pl.read_csv(report / "relations.csv", infer_schema_length=0)
    assert sorted(args["arg-id"].to_list()) == ["Ac1_0", "Ac2_0"]
    assert dict(zip(relations["arg-id"], relations["comment-id"], strict=True)) == {"Ac1_0": "c1", "Ac2_0": "c2"}

    # Each argument now maps to exactly one respondent, so aggregation keeps both attributions.
    arg_rows = list(zip(args["arg-id"], args["argument"], strict=True))
    agg_report, agg_config = _write_report(
        tmp_path / "agg",
        "comment-id,comment-body,attribute_age\nc1,賛成です,20s\nc2,賛成です。,30s\n",
        arg_rows,
        list(zip(relations["arg-id"], relations["comment-id"], strict=True)),
    )
    result = _run(agg_report, agg_config)
    ages = {arg["comment_id"]: arg["attributes"]["age"] for arg in result["arguments"]}
    assert ages == {"c1": "20s", "c2": "30s"}


def _write_classifications(report):
    pl.DataFrame({"arg-id": ["A1_0"], "hate_or_insult": ["yes"]}).write_csv(report / "opinion_classifications.csv")


def test_stale_opinion_classifications_are_ignored_when_disabled(tmp_path):
    report, config = _write_report(
        tmp_path, "comment-id,comment-body,attribute_age\n1,body,20s\n", [("A1_0", "body")], [("A1_0", "1")]
    )
    _write_classifications(report)  # left over from an earlier run with the step enabled
    config["opinion_classification"] = {"enabled": False}
    result = _run(report, config)
    assert result["arguments"][0]["attributes"] == {"age": "20s"}

    del config["opinion_classification"]
    result = _run(report, config)
    assert result["arguments"][0]["attributes"] == {"age": "20s"}


def test_opinion_classifications_are_merged_when_enabled(tmp_path):
    report, config = _write_report(
        tmp_path, "comment-id,comment-body,attribute_age\n1,body,20s\n", [("A1_0", "body")], [("A1_0", "1")]
    )
    _write_classifications(report)
    config["opinion_classification"] = {"enabled": True}
    result = _run(report, config)
    assert result["arguments"][0]["attributes"] == {"age": "20s", "hate_or_insult": "yes"}


def test_failed_classification_fails_the_workflow_when_enabled(tmp_path):
    from analysis_core.compat import normalize_config
    from analysis_core.plugin import PluginRegistry, StepContext, StepOutputs, step_plugin
    from analysis_core.workflow import WorkflowEngine
    from analysis_core.workflows.hierarchical_default import create_hierarchical_workflow

    workflow = create_hierarchical_workflow(include_visualization=False)
    registry = PluginRegistry()
    registry.register_builtin_plugins()
    calls = []

    def make_plugin(step_id, plugin_id):
        @step_plugin(id=plugin_id, version="1.0.0")
        def plugin(ctx, inputs, config):
            calls.append(step_id)
            if step_id == "opinion_classification":
                raise RuntimeError("classification failed")
            return StepOutputs()

        return plugin

    for step in workflow.steps:
        registry.register_or_replace(make_plugin(step.id, step.plugin))
    engine = WorkflowEngine(registry=registry)
    assert engine.registry is registry

    ctx = StepContext(output_dir=tmp_path, input_dir=tmp_path, dataset="report", provider="openai", model="m")
    config = normalize_config({"model": "m"}, include_source_code=False)
    config["opinion_classification"]["enabled"] = True
    result = engine.run(workflow, config, ctx)
    assert result.success is False
    assert "aggregation" not in calls

    calls.clear()
    config["opinion_classification"]["enabled"] = False
    result = engine.run(workflow, config, ctx)
    assert result.success is True
    assert "opinion_classification" not in calls
    assert "aggregation" in calls


def test_custom_intro_counts_comments_after_empty_filter_and_limit(tmp_path):
    comments = "comment-id,comment-body\n1,first\n2,\n3,   \n4,second\n5,third\n"
    report, config = _write_report(tmp_path, comments, [("A1_0", "first")], [("A1_0", "1")])
    result = _run(report, config)
    assert "分析対象となったデータの件数は3件" in result["config"]["intro"]

    config["extraction"]["limit"] = 2
    result = _run(report, config)
    assert "分析対象となったデータの件数は2件" in result["config"]["intro"]


def test_same_opinion_repeated_within_one_comment_writes_one_relation(tmp_path, monkeypatch):
    extraction = importlib.import_module("analysis_core.steps.extraction")
    inputs = tmp_path / "inputs"
    report = tmp_path / "outputs" / "report"
    inputs.mkdir()
    report.mkdir(parents=True)
    (inputs / "input.csv").write_text("comment-id,comment-body\nc1,長い回答\n", encoding="utf-8")
    config = {
        "input": "input",
        "output_dir": "report",
        "provider": "openai",
        "_input_base_dir": str(inputs),
        "_output_base_dir": str(tmp_path / "outputs"),
        "extraction": {"model": "m", "prompt": "p", "workers": 1, "limit": 10, "properties": []},
    }
    monkeypatch.setattr(extraction, "update_progress", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        extraction,
        "request_to_chat_ai",
        lambda **kwargs: ('{"extractedOpinionList": ["Xしてほしい", "Xしてほしい", "Yしてほしい"]}', 1, 1, 2),
    )
    extraction.extraction(config)

    args = pl.read_csv(report / "args.csv", infer_schema_length=0)
    relations = pl.read_csv(report / "relations.csv", infer_schema_length=0)
    assert args["arg-id"].to_list() == ["Ac1_0", "Ac1_2"]
    assert list(zip(relations["arg-id"], relations["comment-id"], strict=True)) == [("Ac1_0", "c1"), ("Ac1_2", "c1")]


def test_duplicated_relation_rows_do_not_duplicate_comment_csv(tmp_path):
    # 修正前の extraction が書いた relations.csv には同じ行が重複していることがある
    report, config = _write_report(
        tmp_path,
        "comment-id,comment-body\nc1,長い回答\n",
        [("Ac1_0", "Xしてほしい"), ("Ac1_2", "Yしてほしい")],
        [("Ac1_0", "c1"), ("Ac1_0", "c1"), ("Ac1_2", "c1")],
    )
    config["is_pubcom"] = True
    result = _run(report, config)
    assert len(result["arguments"]) == 2

    rows = pl.read_csv(report / "final_result_with_comments.csv", infer_schema_length=0)
    assert rows["arg_id"].to_list() == ["Ac1_0", "Ac1_2"]
