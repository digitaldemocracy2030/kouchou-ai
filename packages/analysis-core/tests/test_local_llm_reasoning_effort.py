"""provider=local の reasoning_effort（LOCAL_LLM_REASONING_EFFORT）のテスト

gemma-4 などの思考型モデルは既定で思考してから答えるので、CPU では 1 件あたり 3 倍ほど時間がかかる（#471）。
LOCAL_LLM_REASONING_EFFORT を設定したときだけ、OpenAI 互換の要求に reasoning_effort を付けて送る。
受け付けない接続先もあるので、未設定・空のときは送らない。実 SDK（OpenAI クライアント）から
httpx.MockTransport に送られた要求の本文で確かめる。外部には接続しない。
"""

import json

try:  # openai 2.x までは httpx を使う
    import httpx
except ModuleNotFoundError:  # 新しめの openai は httpx2 を同梱する
    import httpx2 as httpx

import pytest
from openai import OpenAI

from analysis_core.services import llm


@pytest.fixture
def sent(monkeypatch):
    bodies = []

    def handler(request):
        bodies.append(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "id": "x",
                "object": "chat.completion",
                "created": 0,
                "model": "m",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": "ok"},
                        "finish_reason": "stop",
                        "logprobs": None,
                    }
                ],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            },
        )

    transport = httpx.MockTransport(handler)

    def make_client(**kwargs):
        kwargs.pop("http_client", None)
        return OpenAI(**kwargs, http_client=httpx.Client(transport=transport), max_retries=0)

    monkeypatch.setattr(llm, "OpenAI", make_client)
    monkeypatch.delenv("LOCAL_LLM_API_KEY", raising=False)
    return bodies


MESSAGES = [{"role": "user", "content": "hi"}]


@pytest.mark.parametrize("value", [None, "", "  "])
def test_not_sent_when_unset_or_blank(sent, monkeypatch, value):
    if value is None:
        monkeypatch.delenv("LOCAL_LLM_REASONING_EFFORT", raising=False)
    else:
        monkeypatch.setenv("LOCAL_LLM_REASONING_EFFORT", value)
    llm.request_to_local_llm(MESSAGES, "gemma4:e4b", address="127.0.0.1:11434")
    assert "reasoning_effort" not in sent[0]


def test_sent_when_set(sent, monkeypatch):
    monkeypatch.setenv("LOCAL_LLM_REASONING_EFFORT", " none ")
    llm.request_to_local_llm(MESSAGES, "gemma4:e4b", address="127.0.0.1:11434")
    assert sent[0]["reasoning_effort"] == "none"


def test_sent_through_request_to_chat_ai(sent, monkeypatch):
    """パイプラインの各段が使う request_to_chat_ai(provider="local") からも付く"""
    monkeypatch.setenv("LOCAL_LLM_REASONING_EFFORT", "none")
    llm.request_to_chat_ai(MESSAGES, model="gemma4:e4b", provider="local", local_llm_address="127.0.0.1:11434")
    assert sent[0]["reasoning_effort"] == "none"
