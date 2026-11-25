"""Regression tests for the public report attachment command."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

ATTACH_SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "attach_opposition_axes.py"


@pytest.mark.parametrize(
    ("not_applicable", "missing", "expected_scores"),
    [(2, 0, {"a": 1, "b": None, "c": None}), (0, 2, {"a": 1}), (1, 1, None)],
)
def test_attach_axes_distinguishes_absent_scores(
    tmp_path: Path, not_applicable: int, missing: int, expected_scores: dict | None
):
    report_path = tmp_path / "report.json"
    divcon_path = tmp_path / "divcon.json"
    out_path = tmp_path / "out.json"
    report = {
        "clusters": [{"level": 1, "id": "t", "label": "Topic"}],
        "arguments": [{"arg_id": arg, "cluster_ids": ["t"]} for arg in ["a", "b", "c"]],
    }
    divcon = {
        "topics": [{"cluster_id": "t", "label": "Topic", "n": 3}],
        "axes": [
            {
                "id": "axis",
                "cluster_id": "t",
                "name": "Axis",
                "left_pole": "Left",
                "right_pole": "Right",
                "n_scored": 1,
                "n_na": not_applicable,
                "n_missing": missing,
            }
        ],
        "scores": {"axis": [["a", 1, "Reason"]]},
    }
    report_path.write_text(json.dumps(report), encoding="utf-8")
    divcon_path.write_text(json.dumps(divcon), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(ATTACH_SCRIPT), str(report_path), str(divcon_path), "--out", str(out_path)],
        capture_output=True,
        encoding="utf-8",
        check=False,
    )
    if expected_scores is None:
        assert result.returncode == 1
        assert "該当なしと未採点の意見を区別できません: axis" in result.stderr
        assert not out_path.exists()
    else:
        assert result.returncode == 0, result.stderr
        assert json.loads(out_path.read_text(encoding="utf-8"))["opposition_axes"][0]["scores"] == expected_scores
