import copy
import json

import pytest

from analysis_core.validate_output import main, validate_output

REPORT = {
    "clusters": [
        {"id": "0", "parent": "", "label": "all", "takeaway": "", "value": 1},
        {"id": "1", "parent": "0", "label": "one", "takeaway": "", "value": 1},
    ],
    "arguments": [{"arg_id": "a", "argument": "opinion", "x": 0, "y": 1, "cluster_ids": ["0", "1"]}],
}


def test_valid_report_is_not_mutated():
    data = copy.deepcopy(REPORT)
    assert validate_output(data) == []
    assert data == REPORT


@pytest.mark.parametrize("mutate", [
    lambda r: r["clusters"][1].update(parent="missing"),
    lambda r: r["clusters"][1].update(parent="1"),
    lambda r: r["clusters"][1].update(value=-1),
    lambda r: r["arguments"][0].update(cluster_ids=["0", "missing"]),
    lambda r: r["arguments"][0].update(cluster_ids=["1"]),
    lambda r: r["arguments"][0].update(arg_id="0"),
    lambda r: r["arguments"][0].update(x=float("nan")),
    lambda r: r["clusters"].append(r["clusters"][1]),
    lambda r: r["clusters"][1].update(parent=[]),
])
def test_invalid_references_and_values(mutate):
    data = copy.deepcopy(REPORT)
    mutate(data)
    assert validate_output(data)


def test_cli_exit_codes_and_no_original_text_in_errors(tmp_path, capsys):
    path = tmp_path / "report.json"
    assert main([str(path)]) == 2
    path.write_text(json.dumps(REPORT))
    assert main([str(path)]) == 0
    path.write_text('{"clusters": [], "arguments": [], "private": "private original"}')
    assert main([str(path)]) == 1
    assert "private original" not in capsys.readouterr().out
