"""形式不正・途中切れの抽出応答を、その回答だけ有限回取り直すことの回帰テスト（x010）。

200 で返ってきた応答の中身が壊れている場合（JSON の不正・スキーマ違反・finish_reason=length）は
SDK も再試行しないため、1 件でも起きると抽出全体が中断し、成功済みの結果も捨てていた。
"""

import importlib
from types import SimpleNamespace

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
        pytest.param('{"extractedOpinionList": [意見]}', id="malformed-json"),
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
    responder = _Responder('{"extractedOpinionList": [意見]}')
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


@pytest.mark.parametrize(
    "content",
    [
        pytest.param("I'm sorry, but I can't help with that request.", id="text-refusal"),
        pytest.param("申し訳ありませんが、この内容にはお答えできません。", id="text-refusal-ja"),
        pytest.param("", id="empty-content"),
        pytest.param("   \n", id="blank-content"),
    ],
)
def test_text_refusals_without_json_are_not_retried(monkeypatch, content):
    """JSON の括弧を含まない本文（拒否・コンテンツフィルタの空応答）は形式不正ではないので送り直さない（s001）。"""
    responder = _Responder(content)
    monkeypatch.setattr(extraction, "request_to_chat_ai", responder)

    with pytest.raises(ValueError, match="malformed JSON"):
        extraction.extract_arguments("回答", "p", "m")

    assert responder.calls == 1


class _FakeOpenAIClient:
    """llm.OpenAI の代役。chat.completions.create の呼び出し回数を数え、決まった本文を返す。"""

    def __init__(self, content, finish_reason, counter):
        self._content = content
        self._finish_reason = finish_reason
        self._counter = counter
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    def _create(self, **payload):
        self._counter["requests"] += 1
        return SimpleNamespace(
            choices=[
                SimpleNamespace(message=SimpleNamespace(content=self._content), finish_reason=self._finish_reason)
            ],
            usage=CompletionUsage(prompt_tokens=10, completion_tokens=2, total_tokens=12),
        )


@pytest.mark.parametrize(
    ("provider", "model"),
    [
        pytest.param("openrouter", "meta-llama/llama-3.3-70b-instruct:free", id="openrouter-json-fallback"),
        pytest.param("local", "llama3", id="local"),
    ],
)
@pytest.mark.parametrize(
    ("content", "finish_reason"),
    [
        pytest.param("I'm sorry, but I can't help with that request.", "stop", id="text-refusal"),
        pytest.param("", "content_filter", id="content-filter-empty"),
    ],
)
def test_refusals_on_text_paths_are_sent_once(monkeypatch, provider, model, content, finish_reason):
    """OpenRouter の JSON fallback 経路とローカル LLM 経路では、拒否が本文で返る。これを 3 回送らない（s001）。"""
    llm = importlib.import_module("analysis_core.services.llm")
    counter = {"requests": 0}
    monkeypatch.setattr(llm, "OpenAI", lambda *args, **kwargs: _FakeOpenAIClient(content, finish_reason, counter))
    monkeypatch.delenv("OPENROUTER_FORCE_JSON_FALLBACK", raising=False)

    with pytest.raises(ValueError, match="malformed JSON"):
        extraction.extract_arguments("回答", "p", model, provider, None, 30, "sk-test-not-a-real-key")

    assert counter["requests"] == 1


def test_truncated_json_on_text_paths_is_still_retried(monkeypatch):
    """括弧を含む壊れた JSON（途中切れ）は、これまでどおり送り直す。"""
    llm = importlib.import_module("analysis_core.services.llm")
    counter = {"requests": 0}
    monkeypatch.setattr(
        llm,
        "OpenAI",
        lambda *args, **kwargs: _FakeOpenAIClient('{"extractedOpinionList": ["途中', "length", counter),
    )

    with pytest.raises(ValueError, match="malformed JSON"):
        extraction.extract_arguments("回答", "p", "llama3", "local", None, 30)

    assert counter["requests"] == extraction.EXTRACTION_MALFORMED_RESPONSE_MAX_ATTEMPTS


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
