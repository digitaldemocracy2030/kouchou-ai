"""公開用レポート結果 public_result.json のテスト。

public_result.json は hierarchical_result.json から公開してよい項目だけをホワイトリストで写す。
ここに書いていないキーは、どの深さにあっても出てはいけない（ブラックリストだった _public_config と逆）。
"""

import argparse
import json
from pathlib import Path

import pytest

from analysis_core import translate
from analysis_core.public_result import (
    CONFIG_SCALAR_KEYS,
    CONFIG_STEP_KEYS,
    PUBLIC_RESULT_FILENAME,
    PUBLIC_RESULT_SCHEMA_VERSION,
    build_public_result,
    public_result_path,
    write_result_files,
)
from analysis_core.steps.hierarchical_aggregation import hierarchical_aggregation
from analysis_core.steps.hierarchical_layout_generation import hierarchical_layout_generation

SECRET = "sk-test-user-key-should-not-leak"
INTERNAL_PATH = "/srv/kouchou/outputs"
ALLOWED_CONFIG_KEYS = set(CONFIG_SCALAR_KEYS) | {"plan"} | set(CONFIG_STEP_KEYS)


def _full_result() -> dict:
    """hierarchical_result.json 相当。公開してはいけないものを各所に混ぜてある。"""
    return {
        "arguments": [
            {
                "arg_id": "A1_0",
                "argument": "意見",
                "comment_id": "c1",
                "x": 0.1,
                "y": 0.2,
                "p": 0,
                "cluster_ids": ["0", "1_0"],
                "attributes": {"age": "20代", "stance_score": 0.5},
                "url": "https://example.com/c1",
                "embedding": [0.1, 0.2],  # 公開しない
            }
        ],
        "clusters": [
            {
                "level": 0,
                "id": "0",
                "label": "全体",
                "takeaway": "",
                "value": 1,
                "parent": "",
                "density_rank_percentile": 0,
                "debug": {"members": ["A1_0"]},  # 公開しない
            }
        ],
        "comments": {
            "c1": {"comment": "元コメント", "email": "x@example.com"},  # email は公開しない
            "c2": "not a dict",
        },
        # age は hidden_properties に指定した属性なので、公開用の属性表には出さない
        "propertyMap": {"age": {"A1_0": "20代"}, "region": {"A1_0": "東京"}},
        "translations": {
            "en": {"overview": "Overview", "clusters": {"1_0": {"label": "L"}}, "meta": {"model": "gpt"}},
        },
        "overview": "概要",
        "comment_num": 3,
        "layouts": {
            "embedding_umap": {"kind": "point_layout", "points": {"A1_0": {"x": 0.1, "y": 0.2}}, "meta": {}, "tmp": 1},
        },
        "default_layout_id": "embedding_umap",
        "config": {
            "name": "slug-internal",
            "question": "問い",
            "intro": "イントロ",
            "input": "slug-internal",
            "output_dir": "slug-internal",
            "model": "gpt-4o-mini",
            "provider": "openai",
            "analysis_mode": "embedding",
            "is_embedded_at_local": False,
            "enable_source_link": True,
            "enable_original_comments": True,
            "user_api_key": SECRET,
            "_output_base_dir": INTERNAL_PATH,
            "local_llm_address": "http://10.0.0.1:11434",
            "status": "completed",
            "start_time": "2026-01-01",
            "completed_jobs": [{"step": "extraction", "params": {"user_api_key": SECRET}}],
            "lock_until": "2026-01-01",
            "current_job": "",
            "previous": {"user_api_key": SECRET, "question": "旧"},
            "plan": [{"step": "extraction", "run": True, "reason": "first", "internal": {"path": INTERNAL_PATH}}],
            "extraction": {
                "workers": 2,
                "limit": 100,
                "properties": [],
                "categories": {},
                "category_batch_size": 5,
                "source_code": "print(1)",
                "prompt": "抽出プロンプト",
                "model": "gpt-4o-mini",
                "timeout_seconds": 30,
            },
            "embedding": {"model": "text-embedding-3-small", "source_code": "e"},
            "hierarchical_clustering": {"cluster_nums": [3, 6], "source_code": "c", "random_state": 1},
            "hierarchical_initial_labelling": {"workers": 1, "source_code": "i", "prompt": "p", "model": "m"},
            "hierarchical_merge_labelling": {"workers": 1, "source_code": "m", "prompt": "p", "model": "m"},
            "hierarchical_overview": {"source_code": "o", "prompt": "p", "model": "m"},
            "hierarchical_aggregation": {
                "source_code": "a",
                "hidden_properties": {"age": ["10代"]},  # 何を隠したかは公開しない
                "sampling_num": 5000,
            },
            "hierarchical_visualization": {"source_code": "v", "replacements": {"a": ["b"]}},
            "opinion_classification": {"enabled": True, "labels": ["policy_proposal"], "workers": 4},
            "unknown_future_step": {"prompt": "x"},
        },
    }


def test_build_public_result_keeps_only_whitelisted_keys():
    public = build_public_result(_full_result())

    assert public["schema_version"] == PUBLIC_RESULT_SCHEMA_VERSION
    assert public["arguments"] == [
        {
            "arg_id": "A1_0",
            "argument": "意見",
            "comment_id": "c1",
            "x": 0.1,
            "y": 0.2,
            "p": 0,
            "cluster_ids": ["0", "1_0"],
            "attributes": {"age": "20代", "stance_score": 0.5},
            "url": "https://example.com/c1",
        }
    ]
    assert public["clusters"] == [
        {"level": 0, "id": "0", "label": "全体", "takeaway": "", "value": 1, "parent": "", "density_rank_percentile": 0}
    ]
    assert public["comments"] == {"c1": {"comment": "元コメント"}}
    assert public["propertyMap"] == {"region": {"A1_0": "東京"}}
    assert public["translations"] == {"en": {"overview": "Overview", "clusters": {"1_0": {"label": "L"}}}}
    assert public["overview"] == "概要"
    assert public["comment_num"] == 3
    assert public["layouts"] == {
        "embedding_umap": {"kind": "point_layout", "points": {"A1_0": {"x": 0.1, "y": 0.2}}, "meta": {}}
    }
    assert public["default_layout_id"] == "embedding_umap"

    config = public["config"]
    assert set(config) <= ALLOWED_CONFIG_KEYS
    assert config["question"] == "問い"
    assert config["plan"] == [{"step": "extraction", "run": True, "reason": "first"}]
    assert config["extraction"] == {
        "workers": 2,
        "limit": 100,
        "properties": [],
        "categories": {},
        "category_batch_size": 5,
        "source_code": "print(1)",
        "prompt": "抽出プロンプト",
        "model": "gpt-4o-mini",
    }
    assert config["hierarchical_aggregation"] == {"source_code": "a"}
    assert config["hierarchical_visualization"] == {"source_code": "v"}
    assert config["opinion_classification"] == {"enabled": True, "labels": ["policy_proposal"]}

    raw = json.dumps(public, ensure_ascii=False)
    for forbidden in (SECRET, INTERNAL_PATH, "slug-internal", "status", "previous", "completed_jobs", "10代", "email"):
        assert forbidden not in raw, forbidden


def test_build_public_result_does_not_mutate_input_and_tolerates_missing_keys():
    full = _full_result()
    snapshot = json.dumps(full, ensure_ascii=False, sort_keys=True)
    build_public_result(full)
    assert json.dumps(full, ensure_ascii=False, sort_keys=True) == snapshot

    public = build_public_result({})
    assert public == {
        "schema_version": PUBLIC_RESULT_SCHEMA_VERSION,
        "arguments": [],
        "clusters": [],
        "comments": {},
        "propertyMap": {},
        "translations": {},
        "overview": "",
        "config": {},
    }
    # 無い項目（layouts / comment_num）は省略され、None や壊れた型は捨てる
    assert "layouts" not in build_public_result({"layouts": "broken", "comment_num": "3"})


def test_write_result_files_writes_both_files(tmp_path):
    result_path = tmp_path / "hierarchical_result.json"
    public_path = write_result_files(result_path, _full_result())

    assert public_path == public_result_path(result_path) == tmp_path / PUBLIC_RESULT_FILENAME
    assert json.loads(result_path.read_text(encoding="utf-8"))["config"]["user_api_key"] == SECRET
    public_raw = public_path.read_text(encoding="utf-8")
    assert SECRET not in public_raw
    assert json.loads(public_raw)["schema_version"] == PUBLIC_RESULT_SCHEMA_VERSION


def _write_aggregation_fixture(tmp_path: Path) -> tuple[Path, Path]:
    inputs = tmp_path / "inputs"
    outputs = tmp_path / "outputs" / "r1"
    inputs.mkdir()
    outputs.mkdir(parents=True)
    (inputs / "r1.csv").write_text("comment-id,comment-body\nc1,hello\n", encoding="utf-8")
    (outputs / "args.csv").write_text("arg-id,argument\nAc1_0,hello arg\n", encoding="utf-8")
    (outputs / "relations.csv").write_text("arg-id,comment-id\nAc1_0,c1\n", encoding="utf-8")
    (outputs / "hierarchical_clusters.csv").write_text(
        "arg-id,argument,x,y,cluster-level-1-id\nAc1_0,hello arg,0.1,0.2,1_0\n", encoding="utf-8"
    )
    (outputs / "hierarchical_merge_labels.csv").write_text(
        "level,id,label,description,value,parent,density_rank_percentile\n1,1_0,L,D,1,0,0.5\n",
        encoding="utf-8",
    )
    (outputs / "hierarchical_overview.txt").write_text("overview", encoding="utf-8")
    return inputs, outputs


def _aggregation_config(inputs: Path, outputs: Path, **overrides) -> dict:
    config = {
        "output_dir": "r1",
        "input": "r1",
        "question": "q",
        "intro": "i",
        "model": "gpt-4o-mini",
        "provider": "openai",
        "is_pubcom": False,
        "extraction": {"limit": 10, "categories": {}, "prompt": "P"},
        "hierarchical_aggregation": {"hidden_properties": {}},
        "user_api_key": SECRET,
        "_output_base_dir": str(outputs.parent),
        "_input_base_dir": str(inputs),
        "status": "running",
        "previous": {"user_api_key": SECRET, "question": "old"},
    }
    config.update(overrides)
    return config


@pytest.mark.parametrize("enable_original_comments", [False, True])
def test_aggregation_writes_public_result_next_to_result(tmp_path, enable_original_comments):
    inputs, outputs = _write_aggregation_fixture(tmp_path)
    config = _aggregation_config(inputs, outputs, enable_original_comments=enable_original_comments)

    assert hierarchical_aggregation(config) is True

    public_path = outputs / PUBLIC_RESULT_FILENAME
    assert public_path.exists()
    raw = public_path.read_text(encoding="utf-8")
    assert SECRET not in raw
    assert str(tmp_path) not in raw

    public = json.loads(raw)
    result = json.loads((outputs / "hierarchical_result.json").read_text(encoding="utf-8"))
    assert public["schema_version"] == PUBLIC_RESULT_SCHEMA_VERSION
    # 意見・クラスタ・概要は結果ファイルと同じ内容
    assert public["arguments"] == result["arguments"]
    assert public["clusters"] == result["clusters"]
    assert public["overview"] == result["overview"] == "overview"
    assert public["comment_num"] == 1
    # 元コメント本文はレポート単位の opt-in のときだけ
    assert public["comments"] == ({"c1": {"comment": "hello"}} if enable_original_comments else {})
    # config は表示に使う項目だけ。実行状態や前回設定は出ない
    assert set(public["config"]) <= ALLOWED_CONFIG_KEYS
    assert public["config"]["question"] == "q"
    assert public["config"]["intro"] == result["config"]["intro"]
    assert "status" not in public["config"]
    assert "previous" not in public["config"]


def test_aggregation_public_result_drops_hidden_property_columns(tmp_path):
    """hidden_properties に指定した属性は、結果ファイルの属性表には残るが公開用には出ない。"""
    inputs, outputs = _write_aggregation_fixture(tmp_path)
    (inputs / "r1.csv").write_text("comment-id,comment-body,source,region\nc1,hello,internal,東京\n", encoding="utf-8")
    (outputs / "args.csv").write_text(
        "arg-id,argument,source,region\nAc1_0,hello arg,internal,東京\n", encoding="utf-8"
    )
    config = _aggregation_config(
        inputs,
        outputs,
        enable_original_comments=True,
        extraction={"limit": 10, "categories": {"region": {}}, "prompt": "P"},
        hierarchical_aggregation={"hidden_properties": {"source": ["internal"]}},
    )

    assert hierarchical_aggregation(config) is True

    result = json.loads((outputs / "hierarchical_result.json").read_text(encoding="utf-8"))
    public = json.loads((outputs / PUBLIC_RESULT_FILENAME).read_text(encoding="utf-8"))
    # 前提: 集計の結果ファイルは隠すと指定した属性の値を属性表に持っている（既存の挙動）
    assert result["propertyMap"]["source"] == {"Ac1_0": "internal"}
    # 公開用は列ごと外し、他の属性は残す。元コメント本文は集計の段階で除かれている
    assert "source" not in public["propertyMap"]
    assert public["propertyMap"]["region"] == {"Ac1_0": "東京"}
    assert public["comments"] == {}
    assert "internal" not in json.dumps(public, ensure_ascii=False)


def test_layout_generation_refreshes_public_result(tmp_path):
    outputs = tmp_path / "outputs" / "r1"
    outputs.mkdir(parents=True)
    result_path = outputs / "hierarchical_result.json"
    result = {
        "arguments": [
            {"arg_id": "A1_0", "argument": "a", "comment_id": "c1", "x": 1.0, "y": 2.0, "p": 0, "cluster_ids": ["0"]}
        ],
        "clusters": [],
        "comments": {},
        "propertyMap": {},
        "translations": {},
        "overview": "o",
        "comment_num": 1,
        "config": {"question": "q", "user_api_key": SECRET},
    }
    write_result_files(result_path, result)
    before = json.loads((outputs / PUBLIC_RESULT_FILENAME).read_text(encoding="utf-8"))
    assert "layouts" not in before

    hierarchical_layout_generation({"output_dir": "r1", "_output_base_dir": str(outputs.parent)})

    public = json.loads((outputs / PUBLIC_RESULT_FILENAME).read_text(encoding="utf-8"))
    assert public["layouts"]["embedding_umap"]["points"] == {"A1_0": {"x": 1.0, "y": 2.0}}
    assert public["default_layout_id"] == "embedding_umap"
    assert SECRET not in json.dumps(public)


def test_translate_in_place_refreshes_public_result(tmp_path):
    outputs = tmp_path / "outputs" / "r1"
    outputs.mkdir(parents=True)
    result_path = outputs / "hierarchical_result.json"
    result = {
        "arguments": [],
        "clusters": [{"level": 1, "id": "1_0", "label": "L", "takeaway": "D", "value": 1, "parent": "0"}],
        "comments": {},
        "propertyMap": {},
        "translations": {},
        "overview": "概要",
        "comment_num": 1,
        "config": {"question": "問い", "intro": "イントロ", "user_api_key": SECRET},
    }
    write_result_files(result_path, result)

    args = argparse.Namespace(result=result_path, output=None)
    translate._write_outputs(args, result, {"en": {"overview": "Overview", "question": "Q", "intro": "I"}})

    public = json.loads((outputs / PUBLIC_RESULT_FILENAME).read_text(encoding="utf-8"))
    assert public["translations"]["en"]["overview"] == "Overview"
    assert SECRET not in json.dumps(public)

    # 別ファイルへの書き出し（--output）は結果ファイルを触らないので、公開用も作り直さない
    other = tmp_path / "translated.json"
    stamp = (outputs / PUBLIC_RESULT_FILENAME).stat().st_mtime_ns
    translate._write_outputs(argparse.Namespace(result=result_path, output=other), result, {"ko": {"overview": "O"}})
    assert other.exists()
    assert not (tmp_path / PUBLIC_RESULT_FILENAME).exists()
    assert (outputs / PUBLIC_RESULT_FILENAME).stat().st_mtime_ns == stamp


SAMPLE_RESULT = (
    Path(__file__).resolve().parents[3]
    / "utils"
    / "dummy-server"
    / "app"
    / "reports"
    / "example"
    / "hierarchical_result.json"
)


@pytest.mark.skipif(not SAMPLE_RESULT.exists(), reason="同梱サンプルが無い環境")
def test_sample_report_public_result_drops_run_state():
    """同梱のサンプルレポート（旧形式。config に status / completed_jobs / previous が混ざっている）でも契約どおりになる。"""
    result = json.loads(SAMPLE_RESULT.read_text(encoding="utf-8"))
    assert "status" in result["config"]  # 前提: 旧形式のサンプル

    public = build_public_result(result)
    assert set(public["config"]) <= ALLOWED_CONFIG_KEYS
    assert len(public["arguments"]) == len(result["arguments"])
    assert len(public["clusters"]) == len(result["clusters"])
    assert all(
        set(arg) <= {"arg_id", "argument", "comment_id", "x", "y", "p", "cluster_ids", "attributes", "url"}
        for arg in public["arguments"]
    )
