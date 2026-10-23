"""A failed aggregation must fail the run instead of being reported as success."""

import importlib
import json

import pytest

aggregation = importlib.import_module("analysis_core.steps.hierarchical_aggregation")

AGGREGATION_PLAN = [
    "extraction",
    "embedding",
    "hierarchical_clustering",
    "hierarchical_initial_labelling",
    "hierarchical_merge_labelling",
    "hierarchical_overview",
]


def write_report(tmp_path, overview=True):
    inputs = tmp_path / "inputs"
    report = tmp_path / "outputs" / "report"
    inputs.mkdir()
    report.mkdir(parents=True)
    (inputs / "input.csv").write_text("comment-id,comment-body\nc1,good\n")
    (report / "args.csv").write_text("arg-id,argument\na1,opinion\n")
    (report / "relations.csv").write_text("arg-id,comment-id\na1,c1\n")
    (report / "hierarchical_clusters.csv").write_text(
        "arg-id,argument,x,y,cluster-level-1-id\na1,opinion,0.1,0.2,1_0\n"
    )
    (report / "hierarchical_merge_labels.csv").write_text(
        "level,id,label,description,value,parent,density_rank_percentile\n1,1_0,label,desc,1,0,0.5\n"
    )
    if overview:
        (report / "hierarchical_overview.txt").write_text("overview")
    config = {
        "input": "input",
        "output_dir": "report",
        "provider": "openai",
        "model": "m",
        "_input_base_dir": str(inputs),
        "_output_base_dir": str(tmp_path / "outputs"),
        "hierarchical_aggregation": {"hidden_properties": {}},
        "extraction": {"limit": 10, "categories": {}},
        "intro": "intro",
        "is_pubcom": False,
    }
    return report, config


def test_success_still_returns_true(tmp_path):
    report, config = write_report(tmp_path)
    assert aggregation.hierarchical_aggregation(config) is True
    result = json.loads((report / "hierarchical_result.json").read_text())
    assert result["overview"] == "overview"
    assert [a["arg_id"] for a in result["arguments"]] == ["a1"]


def test_missing_input_raises(tmp_path):
    report, config = write_report(tmp_path, overview=False)
    with pytest.raises(FileNotFoundError):
        aggregation.hierarchical_aggregation(config)
    assert not (report / "hierarchical_result.json").exists()


def test_missing_hidden_property_column_raises(tmp_path):
    _, config = write_report(tmp_path)
    config["hierarchical_aggregation"]["hidden_properties"] = {"age": ["10代"]}
    with pytest.raises(ValueError, match="age"):
        aggregation.hierarchical_aggregation(config)


def test_failure_after_json_write_raises(tmp_path, monkeypatch):
    """Missing pubcom CSV must not be hidden behind an already written JSON."""
    _, config = write_report(tmp_path)
    config["is_pubcom"] = True

    def broken(*args, **kwargs):
        raise RuntimeError("pubcom export failed")

    monkeypatch.setattr(aggregation, "add_original_comments", broken)
    with pytest.raises(RuntimeError, match="pubcom export failed"):
        aggregation.hierarchical_aggregation(config)


def test_workflow_marks_run_failed(tmp_path):
    from analysis_core.orchestrator import PipelineOrchestrator

    report, config = write_report(tmp_path)
    config["hierarchical_aggregation"]["hidden_properties"] = {"age": ["10代"]}
    config["plan"] = [{"step": name, "run": False} for name in AGGREGATION_PLAN] + [
        {"step": "hierarchical_aggregation", "run": True}
    ]
    result = PipelineOrchestrator(config).run_default()
    assert not result.success
    assert "age" in (result.error or "")
    status = json.loads((report / "hierarchical_status.json").read_text())
    assert status["status"] == "error"
    assert "hierarchical_aggregation" not in [job["step"] for job in status.get("completed_jobs", [])]


def test_result_json_is_never_visible_partially_written(tmp_path, monkeypatch):
    """書き込み中に公開 API などが読んでも、前回の完全な結果か今回の完全な結果だけが見える。

    以前は hierarchical_result.json を open("w") で直接書き（先に空になる）、さらに
    create_custom_intro が読み直してもう一度書き直していたため、途中の状態が見えた。
    """
    report, config = write_report(tmp_path)
    result_path = report / "hierarchical_result.json"
    result_path.write_text(json.dumps({"old": True}), encoding="utf-8")

    observed = []
    real_dump = json.dump

    def spying_dump(obj, fp, *args, **kwargs):
        # 書き込みのたびに、読み手から見える最終パスの中身を確かめる
        observed.append(json.loads(result_path.read_text(encoding="utf-8")))
        return real_dump(obj, fp, *args, **kwargs)

    monkeypatch.setattr(json, "dump", spying_dump)
    assert aggregation.hierarchical_aggregation(config) is True

    assert observed == [{"old": True}]
    result = json.loads(result_path.read_text(encoding="utf-8"))
    assert result["config"]["intro"].startswith("intro\n分析対象となったデータの件数は1件")
    assert "OpenAI API (m)" in result["config"]["intro"]
    # 呼び出し元の config は書き換えない
    assert config["intro"] == "intro"
    assert not [p.name for p in report.iterdir() if p.name.endswith(".tmp")]


def test_pubcom_csv_is_replaced_atomically(tmp_path, monkeypatch):
    import polars as pl

    report, config = write_report(tmp_path)
    config["is_pubcom"] = True
    final_csv = report / "final_result_with_comments.csv"
    final_csv.write_text("old\n", encoding="utf-8")

    written_paths = []
    real_write_csv = pl.DataFrame.write_csv

    def spying_write_csv(self, file=None, *args, **kwargs):
        written_paths.append(str(file))
        return real_write_csv(self, file, *args, **kwargs)

    monkeypatch.setattr(pl.DataFrame, "write_csv", spying_write_csv)
    assert aggregation.hierarchical_aggregation(config) is True

    assert written_paths and str(final_csv) not in written_paths
    assert "original-comment" in final_csv.read_text(encoding="utf-8")
    assert not [p.name for p in report.iterdir() if p.name.endswith(".tmp")]
