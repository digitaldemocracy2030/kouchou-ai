"""統合ラベリングの親子表は、階層クラスタが入れ子であること（各クラスタの親が 1 つ）を前提にする。"""

import importlib

import polars as pl
import pytest

merge = importlib.import_module("analysis_core.steps.hierarchical_merge_labelling")

ID_COLUMNS = ["cluster-level-1-id", "cluster-level-2-id"]


def _clusters(rows: list[tuple[str, str]]) -> pl.DataFrame:
    return pl.DataFrame({"cluster-level-1-id": [r[0] for r in rows], "cluster-level-2-id": [r[1] for r in rows]})


def test_nested_clusters_get_one_parent_each():
    df = _clusters([("1_0", "2_0"), ("1_0", "2_1"), ("1_1", "2_2"), ("1_1", "2_2")])
    mapping = merge._build_parent_child_mapping(df, ID_COLUMNS)
    parents = {(row["level"], row["id"]): row["parent"] for row in mapping.iter_rows(named=True)}
    assert parents == {
        (1, "1_0"): "0",
        (1, "1_1"): "0",
        (2, "2_0"): "1_0",
        (2, "2_1"): "1_0",
        (2, "2_2"): "1_1",
    }
    assert len(mapping) == len(parents)


def test_cluster_under_two_parents_is_rejected():
    """2_0 が 1_0 と 1_1 の両方にまたがると、join で 2_0 が親違いで 2 回出てしまう。"""
    df = _clusters([("1_0", "2_0"), ("1_1", "2_0"), ("1_1", "2_1")])
    with pytest.raises(
        ValueError, match=r"not nested: 1 cluster\(s\).*level 2 cluster '2_0' is under \['1_0', '1_1'\]"
    ):
        merge._build_parent_child_mapping(df, ID_COLUMNS)
