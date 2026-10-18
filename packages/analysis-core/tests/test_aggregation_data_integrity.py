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
