"""形式不正・途中切れの抽出応答を、その回答だけ有限回取り直すことの回帰テスト（x010）。

200 で返ってきた応答の中身が壊れている場合（JSON の不正・スキーマ違反・finish_reason=length）は
SDK も再試行しないため、1 件でも起きると抽出全体が中断し、成功済みの結果も捨てていた。
"""

import importlib

import openai
import pytest
from openai.types import CompletionUsage
from openai.types.chat import ChatCompletion
from pydantic import ValidationError

extraction = importlib.import_module("analysis_core.steps.extraction")

VALID = '{"extractedOpinionList": ["意見"]}'


def _validation_error() -> ValidationError:
    try:
        extraction.ExtractionResponse.model_validate_json('{"extractedOpinionList": ["途中で')
    except ValidationError as error:
        return error
    raise AssertionError("expected ValidationError")


def _completion(prompt_tokens=5, completion_tokens=7) -> ChatCompletion:
    return ChatCompletion.model_construct(
        id="x",
        choices=[],
        created=0,
        model="m",
        object="chat.completion",
        usage=CompletionUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        ),
    )


class _Responder:
    """request_to_chat_ai の代役。outcomes を先頭から 1 つずつ返す（例外なら送出する）。"""

    def __init__(self, *outcomes):
        self.outcomes = list(outcomes)
        self.calls = 0

    def __call__(self, **kwargs):
        self.calls += 1
        outcome = self.outcomes.pop(0) if len(self.outcomes) > 1 else self.outcomes[0]
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome, 2, 1, 3


@pytest.mark.parametrize(
    "malformed",
    [
        pytest.param("broken JSON", id="malformed-json"),
        pytest.param('{"extractedOpinionList": ["途中で', id="truncated-json"),
        pytest.param("{}", id="schema-mismatch"),
    ],
)
def test_malformed_response_is_retried_for_that_comment_only(monkeypatch, malformed):
    responder = _Responder(malformed, VALID)
    monkeypatch.setattr(extraction, "request_to_chat_ai", responder)

    items, token_input, token_output, token_total = extraction.extract_arguments("回答", "p", "m")

    assert items == ["意見"]
    assert responder.calls == 2
    # 壊れた応答の分も課金されているので、トークンは両方を数える
    assert (token_input, token_output, token_total) == (4, 2, 6)


def test_sdk_validation_error_is_retried(monkeypatch):
    responder = _Responder(_validation_error(), VALID)
    monkeypatch.setattr(extraction, "request_to_chat_ai", responder)

    items, *_ = extraction.extract_arguments("回答", "p", "m")

    assert items == ["意見"]
    assert responder.calls == 2


def test_length_finish_reason_is_retried_and_its_tokens_are_counted(monkeypatch):
    responder = _Responder(openai.LengthFinishReasonError(completion=_completion(5, 7)), VALID)
    monkeypatch.setattr(extraction, "request_to_chat_ai", responder)

    items, token_input, token_output, token_total = extraction.extract_arguments("回答", "p", "m")

    assert items == ["意見"]
    assert responder.calls == 2
    assert (token_input, token_output, token_total) == (7, 8, 15)


def test_retries_are_bounded_and_the_last_error_is_raised(monkeypatch):
    responder = _Responder("broken JSON")
    monkeypatch.setattr(extraction, "request_to_chat_ai", responder)

    with pytest.raises(ValueError, match="malformed JSON"):
        extraction.extract_arguments("回答", "p", "m")

    assert responder.calls == extraction.EXTRACTION_MALFORMED_RESPONSE_MAX_ATTEMPTS == 3


@pytest.mark.parametrize(
    "outcome",
    [
        pytest.param(openai.ContentFilterFinishReasonError(), id="content-filter"),
        pytest.param(None, id="refusal-without-content"),
        pytest.param(RuntimeError("API error"), id="non-format-error"),
    ],
)
def test_refusals_and_non_format_errors_are_not_retried(monkeypatch, outcome):
    responder = _Responder(outcome)
    monkeypatch.setattr(extraction, "request_to_chat_ai", responder)

    with pytest.raises(Exception):  # noqa: B017 - 種類は outcome ごとに異なる
        extraction.extract_arguments("回答", "p", "m")

    assert responder.calls == 1


def test_extraction_completes_when_one_response_is_truncated_once(tmp_path, monkeypatch):
    inputs = tmp_path / "inputs"
    outputs = tmp_path / "outputs"
    inputs.mkdir()
    (outputs / "report").mkdir(parents=True)
    (inputs / "input.csv").write_text("comment-id,comment-body\nc1,一つ目\nc2,二つ目\nc3,三つ目\n")
    config = {
        "input": "input",
        "output_dir": "report",
        "provider": "openai",
        "_input_base_dir": str(inputs),
        "_output_base_dir": str(outputs),
        "extraction": {"model": "m", "prompt": "p", "workers": 2, "limit": 3, "properties": []},
    }
    seen = {"二つ目": 0}

    def request(**kwargs):
        text = kwargs["messages"][-1]["content"]
        if text == "二つ目":
            seen[text] += 1
            if seen[text] == 1:
                return '{"extractedOpinionList": ["途中', 2, 1, 3
        return '{"extractedOpinionList": ["%s の意見"]}' % text, 2, 1, 3

    monkeypatch.setattr(extraction, "request_to_chat_ai", request)

    extraction.extraction(config)

    args = (outputs / "report" / "args.csv").read_text()
    assert "一つ目 の意見" in args and "二つ目 の意見" in args and "三つ目 の意見" in args
    assert seen["二つ目"] == 2
    assert config["total_token_usage"] == 12
