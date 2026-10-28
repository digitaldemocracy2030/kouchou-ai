"""元コメント本文（comments）は enable_original_comments を明示した時だけ公開 JSON に入る。

入力 CSV には引用・再頒布が許されないコメントが混ざりうるため、既定では件数（comment_num）だけを出す。
"""

import json

import polars as pl

from analysis_core.steps.hierarchical_aggregation import hierarchical_aggregation


def _write_report(
    tmp_path,
    comments_csv: str,
    args: list[tuple[str, str]],
    relations: list[tuple[str, str]],
    arg_properties: dict[str, list[str]] | None = None,
):
    inputs = tmp_path / "inputs"
    report = tmp_path / "outputs" / "report"
    inputs.mkdir(parents=True)
    report.mkdir(parents=True)
    (inputs / "input.csv").write_text(comments_csv, encoding="utf-8")
    # hidden_properties に使う属性列は、抽出ステップが args.csv にも書き出す
    pl.DataFrame(
        {"arg-id": [a for a, _ in args], "argument": [t for _, t in args], **(arg_properties or {})}
    ).write_csv(report / "args.csv")
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
        "enable_source_link": False,
        "extraction": {"limit": 1000, "categories": {}},
        "hierarchical_aggregation": {"hidden_properties": {}},
    }
    return report, config


def _run(report, config):
    assert hierarchical_aggregation(config) is True
    return json.loads((report / "hierarchical_result.json").read_text(encoding="utf-8"))


COMMENTS = "comment-id,comment-body,age\n001,first body,20s\n002,second body,30s\n003,no argument,40s\n"
ARGS = [("A001_0", "first"), ("A002_0", "second")]
RELATIONS = [("A001_0", "001"), ("A002_0", "002")]


def test_comments_stay_empty_by_default(tmp_path):
    report, config = _write_report(tmp_path, COMMENTS, ARGS, RELATIONS)
    result = _run(report, config)
    assert result["comments"] == {}
    assert result["comment_num"] == 3
    assert "first body" not in json.dumps(result, ensure_ascii=False)


def test_comments_are_published_only_when_enabled(tmp_path):
    report, config = _write_report(tmp_path, COMMENTS, ARGS, RELATIONS)
    config["enable_original_comments"] = True
    result = _run(report, config)
    # 先頭ゼロの ID をそのまま key にし、意見に紐づいたコメントだけを入れる
    assert result["comments"] == {"001": {"comment": "first body"}, "002": {"comment": "second body"}}
    assert result["config"]["enable_original_comments"] is True
    assert result["comment_num"] == 3


def test_hidden_property_comments_are_not_published(tmp_path):
    report, config = _write_report(tmp_path, COMMENTS, ARGS, RELATIONS, arg_properties={"age": ["20s", "30s"]})
    config["enable_original_comments"] = True
    config["hierarchical_aggregation"]["hidden_properties"] = {"age": ["30s"]}
    result = _run(report, config)
    assert result["comments"] == {"001": {"comment": "first body"}}
