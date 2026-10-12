"""Tests for the OpenRouter structured-output fallback path.

多くの OpenRouter 無料モデルは structured outputs (`beta.chat.completions.parse` /
`response_format=json_schema`) に非対応で、構造化出力を要求すると 400
(BadRequestError) で落ちる。`request_to_openrouter_chatcompletion` は、無料/非対応
モデルでは `chat.completions.create` + `response_format={"type": "json_object"}`
（さらに非対応ならプロンプト強制）へフォールバックして動く経路を提供する。

ここでは実 API を叩かず、client をモックして分岐のみを検証する。
"""

import json

try:  # httpx is openai の HTTP 層で requirements-dev.lock に含まれる（openai 2.x）
    import httpx
except ModuleNotFoundError:  # 新しめの openai(3.x) は httpx2 を同梱する。ローカル uv run 用の保険
    import httpx2 as httpx

import openai
import pytest
from pydantic import BaseModel

from analysis_core.services import llm
from analysis_core.services.llm import (
    _extract_json_text,
    _is_openrouter_free_model,
    _should_use_openrouter_json_fallback,
    _unwrap_openai_json_schema,
    request_to_openrouter_chatcompletion,
)


class _Schema(BaseModel):
    answer: str


def _bad_request(message: str = "response_format is not supported") -> openai.BadRequestError:
    request = httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions")
    response = httpx.Response(400, request=request)
    return openai.BadRequestError(message, response=response, body=None)


class _Usage:
    def __init__(self, prompt=3, completion=5, total=8):
        self.prompt_tokens = prompt
        self.completion_tokens = completion
        self.total_tokens = total


class _Message:
    def __init__(self, content):
        self.content = content


class _Choice:
    def __init__(self, content):
        self.message = _Message(content)


class _Response:
    def __init__(self, content):
        self.choices = [_Choice(content)]
        self.usage = _Usage()


class _FakeParse:
    """beta.chat.completions.parse のモック。"""

    def __init__(self, recorder):
        self._recorder = recorder

    def parse(self, **kwargs):
        self._recorder["parse_calls"].append(kwargs)
        behavior = self._recorder["parse_behavior"]
        if isinstance(behavior, Exception):
            raise behavior
        return _Response(behavior)


class _FakeCreate:
    """chat.completions.create のモック。create_behaviors を 1 呼び出しずつ消費する。"""

    def __init__(self, recorder):
        self._recorder = recorder

    def create(self, **kwargs):
        self._recorder["create_calls"].append(kwargs)
        behaviors = self._recorder["create_behaviors"]
        behavior = behaviors.pop(0) if behaviors else self._recorder["create_default"]
        if isinstance(behavior, Exception):
            raise behavior
        return _Response(behavior)


class _FakeClient:
    def __init__(self, recorder):
        self.chat = type("_Chat", (), {})()
        self.chat.completions = _FakeCreate(recorder)
        self.beta = type("_Beta", (), {})()
        self.beta.chat = type("_BetaChat", (), {})()
        self.beta.chat.completions = _FakeParse(recorder)


@pytest.fixture
def recorder(monkeypatch):
    rec = {
        "parse_calls": [],
        "create_calls": [],
        "parse_behavior": '{"answer": "from-parse"}',
        "create_behaviors": [],
        "create_default": '{"answer": "from-create"}',
        "init_kwargs": None,
    }

    def _factory(**kwargs):
        rec["init_kwargs"] = kwargs
        return _FakeClient(rec)

    monkeypatch.setattr(llm, "OpenAI", _factory)
    monkeypatch.delenv("OPENROUTER_FORCE_JSON_FALLBACK", raising=False)
    return rec


# --- helper 単体テスト -------------------------------------------------------


def test_is_openrouter_free_model():
    assert _is_openrouter_free_model("deepseek/deepseek-chat-v3-0324:free") is True
    assert _is_openrouter_free_model("openai/gpt-4o") is False
    assert _is_openrouter_free_model(None) is False


def test_should_use_json_fallback_env_override(monkeypatch):
    monkeypatch.setenv("OPENROUTER_FORCE_JSON_FALLBACK", "1")
    assert _should_use_openrouter_json_fallback("openai/gpt-4o") is True
    monkeypatch.setenv("OPENROUTER_FORCE_JSON_FALLBACK", "false")
    assert _should_use_openrouter_json_fallback("x/y:free") is False
    monkeypatch.delenv("OPENROUTER_FORCE_JSON_FALLBACK", raising=False)
    assert _should_use_openrouter_json_fallback("x/y:free") is True


def test_extract_json_text_strips_code_fence():
    fenced = '```json\n{"answer": "hi"}\n```'
    assert json.loads(_extract_json_text(fenced)) == {"answer": "hi"}


def test_extract_json_text_extracts_from_surrounding_prose():
    noisy = 'Sure, here is the result: {"answer": "hi"} hope it helps!'
    assert json.loads(_extract_json_text(noisy)) == {"answer": "hi"}


def test_unwrap_openai_json_schema():
    wrapped = {"type": "json_schema", "json_schema": {"name": "S", "schema": {"type": "object"}}}
    assert _unwrap_openai_json_schema(wrapped) == {"type": "object"}
    assert _unwrap_openai_json_schema({"type": "json_object"}) is None


# --- 分岐テスト -------------------------------------------------------------


def test_normal_model_uses_structured_parse(recorder):
    content, *_ = request_to_openrouter_chatcompletion(
        messages=[{"role": "user", "content": "q"}],
        model="openai/gpt-4o",
        json_schema=_Schema,
        user_api_key="test-key",
    )
    assert content == '{"answer": "from-parse"}'
    assert len(recorder["parse_calls"]) == 1
    assert len(recorder["create_calls"]) == 0


def test_free_model_skips_parse_and_uses_json_object(recorder):
    content, *_ = request_to_openrouter_chatcompletion(
        messages=[{"role": "user", "content": "q"}],
        model="deepseek/deepseek-chat-v3-0324:free",
        json_schema=_Schema,
        user_api_key="test-key",
    )
    assert content == '{"answer": "from-create"}'
    # parse は呼ばれず、create が json_object で呼ばれる
    assert len(recorder["parse_calls"]) == 0
    assert len(recorder["create_calls"]) == 1
    assert recorder["create_calls"][0]["response_format"] == {"type": "json_object"}
    # スキーマがプロンプトへ注入されている
    injected = recorder["create_calls"][0]["messages"][-1]["content"]
    assert "JSON Schema" in injected


def test_non_free_model_falls_back_on_bad_request(recorder):
    recorder["parse_behavior"] = _bad_request()
    content, *_ = request_to_openrouter_chatcompletion(
        messages=[{"role": "user", "content": "q"}],
        model="some/structured-unsupported-model",
        json_schema=_Schema,
        user_api_key="test-key",
    )
    assert content == '{"answer": "from-create"}'
    assert len(recorder["parse_calls"]) == 1  # まず parse を試みる
    assert len(recorder["create_calls"]) == 1  # 失敗して create へ
    assert recorder["create_calls"][0]["response_format"] == {"type": "json_object"}


def test_json_object_unsupported_drops_to_plain_prompt(recorder):
    recorder["parse_behavior"] = _bad_request()
    # 1 回目 create(json_object) も 400、2 回目(response_format 無し) で成功
    recorder["create_behaviors"] = [_bad_request("json_object unsupported"), '{"answer": "plain"}']
    content, *_ = request_to_openrouter_chatcompletion(
        messages=[{"role": "user", "content": "q"}],
        model="some/very-limited-model",
        json_schema=_Schema,
        user_api_key="test-key",
    )
    assert content == '{"answer": "plain"}'
    assert len(recorder["create_calls"]) == 2
    assert recorder["create_calls"][0]["response_format"] == {"type": "json_object"}
    assert "response_format" not in recorder["create_calls"][1]


def test_fallback_cleans_markdown_fenced_json(recorder):
    recorder["create_default"] = '```json\n{"answer": "fenced"}\n```'
    content, *_ = request_to_openrouter_chatcompletion(
        messages=[{"role": "user", "content": "q"}],
        model="x/y:free",
        json_schema=_Schema,
        user_api_key="test-key",
    )
    assert json.loads(content) == {"answer": "fenced"}


def test_dict_json_schema_free_model_uses_fallback(recorder):
    schema = {"type": "json_schema", "json_schema": {"name": "S", "schema": {"type": "object"}}}
    content, *_ = request_to_openrouter_chatcompletion(
        messages=[{"role": "user", "content": "q"}],
        model="x/y:free",
        json_schema=schema,
        user_api_key="test-key",
    )
    assert content == '{"answer": "from-create"}'
    assert len(recorder["create_calls"]) == 1
    assert recorder["create_calls"][0]["response_format"] == {"type": "json_object"}


def test_plain_text_request_unchanged(recorder):
    recorder["create_default"] = "hello world"
    content, *_ = request_to_openrouter_chatcompletion(
        messages=[{"role": "user", "content": "q"}],
        model="openai/gpt-4o",
        user_api_key="test-key",
    )
    assert content == "hello world"
    assert len(recorder["parse_calls"]) == 0
    assert len(recorder["create_calls"]) == 1
    assert "response_format" not in recorder["create_calls"][0]


def test_is_json_request_uses_json_object(recorder):
    content, *_ = request_to_openrouter_chatcompletion(
        messages=[{"role": "user", "content": "q"}],
        model="openai/gpt-4o",
        is_json=True,
        user_api_key="test-key",
    )
    assert content == '{"answer": "from-create"}'
    assert recorder["create_calls"][0]["response_format"] == {"type": "json_object"}
