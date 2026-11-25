"""Exercise the production aggregation and public writer from contract cases."""

import contextlib
import io

import polars as pl

from analysis_core.public_result import build_public_result
from analysis_core.steps.hierarchical_aggregation import _build_arguments


def write_public(case):
    arguments = case["arguments"]
    comments = case["comments"]
    if case["relations"] is not None:
        clusters = pl.DataFrame(
            [{"arg-id": row["arg_id"], "argument": row["arg_id"], "x": 0, "y": 0} for row in arguments],
            schema={"arg-id": pl.String, "argument": pl.String, "x": pl.Int64, "y": pl.Int64},
        )
        source_rows = pl.DataFrame(
            [{"comment-id": row["id"], "comment-body": row["body"]} for row in comments],
            schema={"comment-id": pl.String, "comment-body": pl.String},
        )
        relations = pl.DataFrame(
            [{"arg-id": row["opinion"], "comment-id": row["source"]} for row in case["relations"]],
            schema={"arg-id": pl.String, "comment-id": pl.String},
        )
        with contextlib.redirect_stdout(io.StringIO()):
            arguments = _build_arguments(clusters, source_rows, relations, {})

    report = {
        "arguments": arguments,
        "comments": {row["id"]: {"comment": row["body"]} for row in comments},
        "config": {"enable_original_comments": case["publish"]},
    }
    if case["inputCount"] is not None:
        report["comment_num"] = case["inputCount"]
    try:
        return build_public_result(report)
    except ValueError:
        return {"error": True}
