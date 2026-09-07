import json

import pytest
from analysis_core.services.parse_json_list import parse_extraction_response


@pytest.mark.parametrize("items", [[], ["テスト1", "テスト2"]])
@pytest.mark.parametrize("serialized", [False, True])
def test_valid_extraction_response(items, serialized):
    response = {"extractedOpinionList": items}
    assert parse_extraction_response(json.dumps(response) if serialized else response) == items


@pytest.mark.parametrize(
    "response",
    [
        {},
        {"extractedOpinionList": None},
        {"extractedOpinionList": "opinion"},
        {"extractedOpinionList": [1]},
        {"extractedOpinionList": [{}]},
        [],
        None,
    ],
)
@pytest.mark.parametrize("serialized", [False, True])
def test_invalid_extraction_response_raises(response, serialized):
    with pytest.raises(ValueError, match="Invalid extraction response"):
        parse_extraction_response(json.dumps(response) if serialized else response)


def test_invalid_json_does_not_return_empty_or_expose_response():
    with pytest.raises(ValueError, match="malformed JSON") as error:
        parse_extraction_response("private response {")
    assert "private response" not in str(error.value)
