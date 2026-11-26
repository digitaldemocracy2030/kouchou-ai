import polars as pl
import pytest

from analysis_core.public_result import build_public_result
from analysis_core.steps.hierarchical_aggregation import _build_arguments


@pytest.mark.parametrize("publish", [True, False])
def test_aggregation_and_public_writer_keep_every_source(publish):
    clusters = pl.DataFrame({"arg-id": ["X", "Y"], "argument": ["x", "y"], "x": [0.0, 1.0], "y": [0.0, 0.0]})
    first, second = "001", "9007199254740993"
    comments = pl.DataFrame({"comment-id": [first, second], "attribute_age": ["20代", "40代"]})
    relations = pl.DataFrame({"arg-id": ["X", "Y", "X", "X"], "comment-id": [first, first, second, first]})
    result = build_public_result(
        {
            "arguments": _build_arguments(clusters, comments, relations, {}),
            "comments": {
                first: {"comment": "A"},
                second: {"comment": "B"},
                "unused": {"comment": "no linked opinion"},
            },
            "config": {"enable_original_comments": publish},
            "comment_num": 3,
        }
    )
    assert result["arguments"][0]["comment_ids"] == [first, second]
    assert result["arguments"][0]["comment_id"] == first
    assert result["arguments"][0]["attributes"] == {"age": "20代"}
    assert "comment_ids" not in result["arguments"][1]
    assert result["arguments"][1]["comment_id"] == first
    assert result["comments"] == ({first: {"comment": "A"}, second: {"comment": "B"}} if publish else {})
    assert result["comment_num"] == 3


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ({"comment_id": 7}, {"comment_id": "7"}),
        ({"comment_id": 185001345000000001}, {"comment_id": "185001345000000001"}),
        ({"comment_id": 7.0}, {"comment_id": "7"}),
        ({"comment_id": "001"}, {"comment_id": "001"}),
        (
            {"comment_id": "unused", "comment_ids": ["001", "1", "001"]},
            {"comment_id": "001", "comment_ids": ["001", "1"]},
        ),
        ({"comment_id": "unused", "comment_ids": []}, {"comment_id": ""}),
    ],
)
def test_public_writer_accepts_legacy_references_without_bodies(source, expected):
    public = build_public_result({"arguments": [{"arg_id": "X", **source}]})
    assert public["arguments"] == [{"arg_id": "X", **expected}]
    assert public["comments"] == {}


@pytest.mark.parametrize("source", [{"comment_id": 2.5}, {"comment_id": True}, {"comment_ids": [123]}])
def test_public_writer_rejects_ambiguous_ids(source):
    with pytest.raises(ValueError, match="comment_id"):
        build_public_result({"arguments": [{"arg_id": "X", **source}]})
