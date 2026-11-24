"""結果 JSON（hierarchical_result.json）とパブコメ CSV の中身を、2 階層・属性列ありの入力で丸ごと確かめる。

公開ビューアは arguments の cluster_ids、clusters の value・parent・density_rank_percentile、
comments を使い、管理画面はパブコメ CSV をダウンロードさせる。どれも件数や存在だけでなく値まで固定する。
"""

import csv
import importlib
import io
import json

import polars as pl
import pytest

aggregation = importlib.import_module("analysis_core.steps.hierarchical_aggregation")

# 先頭に「意見が出なかったコメント（004）」、途中に非公開の属性値（age=30s）を持つコメント（002）を置く。
# どちらも読み飛ばす対象で、その後ろのコメントが落ちないことを確かめるため
COMMENTS_CSV = (
    "comment-id,comment-body,url,source,age,attribute_age,attribute_area\n"
    "004,意見の出なかったコメント,https://example.invalid/4,web,40s,40s,京都\n"
    "001,最初のコメント,https://example.invalid/1,web,20s,20s,東京\n"
    "002,二つ目のコメント,https://example.invalid/2,paper,30s,30s,\n"
    "003,三つ目のコメント,,web,,,大阪\n"
)
ARGS = [
    ("A001_0", "交通を良くする", "pos", "20s"),
    ("A001_1", "公園を増やす", "neg", "20s"),
    ("A002_0", "税を下げる", "pos", "30s"),
    ("A003_0", "図書館を広げる", "neg", ""),
]


def _write_report(tmp_path, *, is_pubcom=True, translation=None):
    inputs = tmp_path / "inputs"
    report = tmp_path / "outputs" / "report"
    inputs.mkdir(parents=True)
    report.mkdir(parents=True)
    (inputs / "input.csv").write_text(COMMENTS_CSV, encoding="utf-8")
    pl.DataFrame(
        {
            "arg-id": [a[0] for a in ARGS],
            "argument": [a[1] for a in ARGS],
            "sentiment": [a[2] for a in ARGS],
            "age": [a[3] for a in ARGS],
        }
    ).write_csv(report / "args.csv")
    (report / "relations.csv").write_text(
        "arg-id,comment-id\nA001_0,001\nA001_1,001\nA002_0,002\nA003_0,003\n", encoding="utf-8"
    )
    pl.DataFrame(
        {
            "arg-id": [a[0] for a in ARGS],
            "argument": [a[1] for a in ARGS],
            "x": [0.1, 0.2, 0.3, 0.4],
            "y": [1.0, 2.0, 3.0, 4.0],
            "cluster-level-1-id": ["1_0", "1_0", "1_1", "1_1"],
            "cluster-level-2-id": ["2_0", "2_1", "2_2", "2_2"],
        }
    ).write_csv(report / "hierarchical_clusters.csv")
    (report / "hierarchical_merge_labels.csv").write_text(
        "level,id,label,description,value,parent,density_rank_percentile\n"
        "1,1_0,まちづくり,街の話,2,0,0.5\n"
        "1,1_1,暮らし,暮らしの話,2,0,1.0\n"
        "2,2_0,交通,交通の話,1,1_0,0.25\n"
        "2,2_1,公園,公園の話,1,1_0,0.75\n"
        "2,2_2,税と図書館,税と図書館の話,2,1_1,1.0\n",
        encoding="utf-8",
    )
    (report / "hierarchical_overview.txt").write_text("全体の概要", encoding="utf-8")
    config = {
        "name": "report",
        "input": "input",
        "output_dir": "report",
        "_input_base_dir": str(inputs),
        "_output_base_dir": str(tmp_path / "outputs"),
        "intro": "はじめに",
        "question": "問い",
        "provider": "openai",
        "model": "gpt-4o-mini",
        "is_pubcom": is_pubcom,
        "enable_source_link": True,
        "enable_original_comments": True,
        "extraction": {"limit": 1000, "categories": {"sentiment": {"pos": "賛成", "neg": "反対"}}},
        "hierarchical_aggregation": {"hidden_properties": {"age": ["30s"]}},
    }
    if translation is not None:
        config["translation"] = translation
    return report, config


def _run(tmp_path, **kwargs):
    report, config = _write_report(tmp_path, **kwargs)
    assert aggregation.hierarchical_aggregation(config) is True
    return report, json.loads((report / "hierarchical_result.json").read_text(encoding="utf-8"))


def test_arguments_carry_cluster_path_text_and_source(tmp_path):
    _, result = _run(tmp_path)
    assert result["arguments"] == [
        {
            "arg_id": "A001_0",
            "argument": "交通を良くする",
            "comment_id": "001",
            "x": 0.1,
            "y": 1.0,
            "p": 0,
            "cluster_ids": ["0", "1_0", "2_0"],
            "attributes": {"age": "20s", "area": "東京"},
            "url": "https://example.invalid/1",
        },
        {
            "arg_id": "A001_1",
            "argument": "公園を増やす",
            "comment_id": "001",
            "x": 0.2,
            "y": 2.0,
            "p": 0,
            "cluster_ids": ["0", "1_0", "2_1"],
            "attributes": {"age": "20s", "area": "東京"},
            "url": "https://example.invalid/1",
        },
        {
            "arg_id": "A002_0",
            "argument": "税を下げる",
            "comment_id": "002",
            "x": 0.3,
            "y": 3.0,
            "p": 0,
            "cluster_ids": ["0", "1_1", "2_2"],
            "attributes": {"age": "30s", "area": None},
            "url": "https://example.invalid/2",
        },
        {
            "arg_id": "A003_0",
            "argument": "図書館を広げる",
            "comment_id": "003",
            "x": 0.4,
            "y": 4.0,
            "p": 0,
            "cluster_ids": ["0", "1_1", "2_2"],
            "attributes": {"age": None, "area": "大阪"},
            "url": None,
        },
    ]


def test_clusters_include_root_and_keep_value_parent_density(tmp_path):
    _, result = _run(tmp_path)
    assert result["clusters"] == [
        {
            "level": 0,
            "id": "0",
            "label": "全体",
            "takeaway": "",
            "value": 4,
            "parent": "",
            "density_rank_percentile": 0,
        },
        {
            "level": 1,
            "id": "1_0",
            "label": "まちづくり",
            "takeaway": "街の話",
            "value": 2,
            "parent": "0",
            "density_rank_percentile": 0.5,
        },
        {
            "level": 1,
            "id": "1_1",
            "label": "暮らし",
            "takeaway": "暮らしの話",
            "value": 2,
            "parent": "0",
            "density_rank_percentile": 1.0,
        },
        {
            "level": 2,
            "id": "2_0",
            "label": "交通",
            "takeaway": "交通の話",
            "value": 1,
            "parent": "1_0",
            "density_rank_percentile": 0.25,
        },
        {
            "level": 2,
            "id": "2_1",
            "label": "公園",
            "takeaway": "公園の話",
            "value": 1,
            "parent": "1_0",
            "density_rank_percentile": 0.75,
        },
        {
            "level": 2,
            "id": "2_2",
            "label": "税と図書館",
            "takeaway": "税と図書館の話",
            "value": 2,
            "parent": "1_1",
            "density_rank_percentile": 1.0,
        },
    ]


def test_comments_skip_unused_and_hidden_but_keep_the_rest(tmp_path):
    """意見の出なかったコメントと、非公開の属性値を持つコメントは本文を出さない。その後ろのコメントは残す。"""
    _, result = _run(tmp_path)
    assert result["comments"] == {"001": {"comment": "最初のコメント"}, "003": {"comment": "三つ目のコメント"}}


def test_intro_states_the_counts(tmp_path):
    _, result = _run(tmp_path)
    assert "データの件数は4件" in result["config"]["intro"]
    assert "4件の意見（議論）を抽出" in result["config"]["intro"]


def test_pubcom_csv_keeps_source_url_attributes_and_category(tmp_path):
    """管理画面がダウンロードさせるパブコメ CSV。入力の url・source・attribute_ 列があっても組み立てられる。"""
    report, _ = _run(tmp_path)
    rows = list(csv.reader(io.StringIO((report / "final_result_with_comments.csv").read_text(encoding="utf-8"))))
    assert rows == [
        [
            "comment-id",
            "original-comment",
            "arg_id",
            "argument",
            "category_id",
            "category",
            "source",
            "url",
            "attribute_age",
            "attribute_area",
        ],
        [
            "001",
            "最初のコメント",
            "A001_0",
            "交通を良くする",
            "1_0",
            "まちづくり",
            "web",
            "https://example.invalid/1",
            "20s",
            "東京",
        ],
        [
            "001",
            "最初のコメント",
            "A001_1",
            "公園を増やす",
            "1_0",
            "まちづくり",
            "web",
            "https://example.invalid/1",
            "20s",
            "東京",
        ],
        [
            "002",
            "二つ目のコメント",
            "A002_0",
            "税を下げる",
            "1_1",
            "暮らし",
            "paper",
            "https://example.invalid/2",
            "30s",
            "",
        ],
        ["003", "三つ目のコメント", "A003_0", "図書館を広げる", "1_1", "暮らし", "web", "", "", "大阪"],
    ]


def test_translation_languages_require_the_translations_file(tmp_path):
    """翻訳の言語を指定したのに translations.json が無いときは、訳の無い結果を黙って作らない。"""
    report, config = _write_report(tmp_path, translation={"languages": ["en"]})
    with pytest.raises(FileNotFoundError, match="translation.languages"):
        aggregation._build_translations(config, {})


def test_no_translation_languages_and_no_file_is_fine(tmp_path):
    report, config = _write_report(tmp_path)
    assert aggregation._build_translations(config, {}) == {}
