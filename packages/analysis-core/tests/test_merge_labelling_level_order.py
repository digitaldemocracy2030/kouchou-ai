"""統合ラベリングは階層を数値順に下から上へ処理する（cluster_nums が 10 段以上でも壊れない）。"""

import importlib

import polars as pl

merge = importlib.import_module("analysis_core.steps.hierarchical_merge_labelling")

N_ARGS = 12
N_LEVELS = 11


def _level_id(level: int, i: int) -> str:
    # level L では先頭 L 件が単独のクラスタ、残りが 1 つのクラスタになる（入れ子が保たれる）
    return f"{level}_{min(i, level)}"


def _write_inputs(report_dir):
    rows = []
    for i in range(N_ARGS):
        row = {"arg-id": f"A{i}", "argument": f"意見{i}", "x": float(i), "y": float(i % 3)}
        for level in range(1, N_LEVELS + 1):
            row[f"cluster-level-{level}-id"] = _level_id(level, i)
        row[f"cluster-level-{N_LEVELS}-label"] = f"葉{i}"
        row[f"cluster-level-{N_LEVELS}-description"] = f"葉{i}の説明"
        rows.append(row)
    df = pl.DataFrame(rows)
    df.write_csv(report_dir / "hierarchical_initial_labels.csv")
    df.select(["arg-id", "argument", "x", "y"] + [f"cluster-level-{lv}-id" for lv in range(1, N_LEVELS + 1)]).write_csv(
        report_dir / "hierarchical_clusters.csv"
    )


def test_merge_labelling_handles_ten_or_more_levels(tmp_path, monkeypatch):
    report_dir = tmp_path / "report"
    report_dir.mkdir()
    _write_inputs(report_dir)

    def fake_request(**kwargs):
        return {"label": "統合", "description": "統合した説明"}, 1, 1, 2

    monkeypatch.setattr(merge, "request_to_chat_ai", fake_request)
    config = {
        "output_dir": "report",
        "_output_base_dir": str(tmp_path),
        "provider": "openai",
        "hierarchical_merge_labelling": {"sampling_num": 3, "prompt": "p", "model": "m", "workers": 1},
    }

    merge.hierarchical_merge_labelling(config)

    result = pl.read_csv(report_dir / "hierarchical_merge_labels.csv")
    counts = dict(result.group_by("level").len().iter_rows())
    assert counts == {level: level + 1 for level in range(1, N_LEVELS + 1)}
    assert result["label"].null_count() == 0
    # 最上位の親は全体クラスタ "0"、各階層の value の合計は意見数に等しい
    assert set(result.filter(pl.col("level") == 1)["parent"].cast(pl.Utf8).to_list()) == {"0"}
    for level in range(1, N_LEVELS + 1):
        assert result.filter(pl.col("level") == level)["value"].sum() == N_ARGS
    # 最下層のラベルは初期ラベリングの値のまま
    leaves = result.filter(pl.col("level") == N_LEVELS).sort("id")
    assert set(leaves["label"].to_list()) == {f"葉{i}" for i in range(N_ARGS)}
