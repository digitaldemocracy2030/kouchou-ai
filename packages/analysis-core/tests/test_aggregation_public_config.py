"""hierarchical_result.json の config に非公開情報が残らないことのテスト。

hierarchical_result.json は公開 API・静的エクスポート・Blob 同期で配布されるため、
ユーザー入力の API キーやサーバー内部パスを書き出してはいけない。
"""

import json

from analysis_core.steps.hierarchical_aggregation import _public_config, hierarchical_aggregation

SECRET = "sk-test-user-key-should-not-leak"


def _write_fixture(tmp_path):
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


def test_result_config_excludes_secrets_and_internal_paths(tmp_path):
    inputs, outputs = _write_fixture(tmp_path)
    config = {
        "output_dir": "r1",
        "input": "r1",
        "question": "q",
        "intro": "i",
        "model": "gpt-4o-mini",
        "provider": "openai",
        "is_pubcom": False,
        "extraction": {"limit": 10, "categories": {}},
        "hierarchical_aggregation": {"hidden_properties": {}},
        "user_api_key": SECRET,
        "_output_base_dir": str(outputs.parent),
        "_input_base_dir": str(inputs),
        "previous": {"user_api_key": SECRET, "error_stack_trace": "Traceback ...", "question": "old"},
    }

    assert hierarchical_aggregation(config) is True

    raw = (outputs / "hierarchical_result.json").read_text(encoding="utf-8")
    assert SECRET not in raw
    assert str(tmp_path) not in raw
    assert "Traceback" not in raw

    result_config = json.loads(raw)["config"]
    assert result_config["question"] == "q"
    assert result_config["model"] == "gpt-4o-mini"
    assert result_config["previous"] == {"question": "old"}
    # 後続処理（create_custom_intro 等）が使う元の config は変更しない
    assert config["user_api_key"] == SECRET
    assert config["_output_base_dir"] == str(outputs.parent)


def test_public_config_is_recursive_and_non_mutating():
    config = {"a": 1, "_x": 2, "nested": [{"user_api_key": "k", "b": 3}]}
    assert _public_config(config) == {"a": 1, "nested": [{"b": 3}]}
    assert config["nested"][0]["user_api_key"] == "k"
