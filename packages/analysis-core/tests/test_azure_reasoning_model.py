"""Azure の推論モデル判定（temperature を送るかどうか）のテスト

推論モデル（o 系 / GPT-5,6 系）は temperature=0 を 400（unsupported_value）で拒否する。
Azure のデプロイ名は管理者が自由に付けるので、デプロイ名だけでは推論モデルか分からない。
AZURE_CHATCOMPLETION_MODEL_NAME（実モデル名）と AZURE_CHATCOMPLETION_REASONING（明示指定）で
判定できることを、実 SDK（AzureOpenAI）から送られる HTTP リクエストの中身で確かめる。
外部には接続せず、httpx.MockTransport で応答する。
"""

import json

try:  # openai 2.x までは httpx を使う
    import httpx
except ModuleNotFoundError:  # 新しめの openai は httpx2 を同梱する
    import httpx2 as httpx

import pytest
from openai import AzureOpenAI
from pydantic import BaseModel

from analysis_core.services import llm


class _Answer(BaseModel):
    answer: str


def _completion(content: str) -> dict:
    return {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "created": 0,
        "model": "test",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
                "logprobs": None,
            }
        ],
        "usage": {"prompt_tokens": 3, "completion_tokens": 5, "total_tokens": 8},
    }


@pytest.fixture
def azure(monkeypatch):
    """AzureOpenAI の通信先を MockTransport に差し替え、送られた JSON 本文を記録する"""
    sent: list[dict] = []

    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content)
        sent.append(body)
        # Azure の推論モデルと同じく、temperature≠1 を 400 で拒否する応答を返せるようにする
        if state["reject_temperature"] and "temperature" in body and body["temperature"] != 1:
            return httpx.Response(
                400,
                json={
                    "error": {
                        "message": "Unsupported value: 'temperature' does not support 0 with this model.",
                        "type": "invalid_request_error",
                        "param": "temperature",
                        "code": "unsupported_value",
                    }
                },
            )
        return httpx.Response(200, json=_completion('{"answer": "ok"}'))

    state = {"reject_temperature": False}
    transport = httpx.MockTransport(handler)

    def make_client(**kwargs):
        return AzureOpenAI(**kwargs, http_client=httpx.Client(transport=transport), max_retries=0)

    monkeypatch.setattr(llm, "AzureOpenAI", make_client)
    monkeypatch.setenv("AZURE_CHATCOMPLETION_ENDPOINT", "https://example.invalid")
    monkeypatch.setenv("AZURE_CHATCOMPLETION_API_KEY", "dummy-key")
    monkeypatch.setenv("AZURE_CHATCOMPLETION_VERSION", "2024-10-21")
    monkeypatch.delenv("AZURE_CHATCOMPLETION_MODEL_NAME", raising=False)
    monkeypatch.delenv("AZURE_CHATCOMPLETION_REASONING", raising=False)

    class Env:
        def __init__(self):
            self.sent = sent

        def configure(self, deployment, model_name=None, reasoning=None, reject_temperature=False):
            monkeypatch.setenv("AZURE_CHATCOMPLETION_DEPLOYMENT_NAME", deployment)
            if model_name is not None:
                monkeypatch.setenv("AZURE_CHATCOMPLETION_MODEL_NAME", model_name)
            if reasoning is not None:
                monkeypatch.setenv("AZURE_CHATCOMPLETION_REASONING", reasoning)
            state["reject_temperature"] = reject_temperature

    return Env()


MESSAGES = [{"role": "user", "content": "hello"}]

# parse（pydantic）・json_object・素のチャットの 3 経路
PATHS = [
    pytest.param({"json_schema": _Answer}, id="parse"),
    pytest.param({"is_json": True}, id="json"),
    pytest.param({}, id="plain"),
]


def _call(kwargs):
    # tenacity の再試行を待たないよう、デコレートされていない本体を呼ぶ
    return llm.request_to_azure_chatcompletion.__wrapped__(MESSAGES, **kwargs)


@pytest.mark.parametrize("kwargs", PATHS)
def test_reasoning_model_name_with_custom_deployment_omits_temperature(azure, kwargs):
    """デプロイ名がモデル名と違っても、MODEL_NAME が推論モデルなら temperature を送らない"""
    azure.configure("kouchou-chat", model_name="gpt-5-mini", reject_temperature=True)

    _call(kwargs)

    assert len(azure.sent) == 1
    assert "temperature" not in azure.sent[0]
    assert azure.sent[0]["seed"] == 0


# MODEL_NAME に表示名（モデル ID の形でない値）を入れ、デプロイ名はモデル名どおりにしている既存環境
DISPLAY_NAME_WITH_MODEL_DEPLOYMENT = [
    pytest.param("gpt-5-mini", "Azure GPT-5 mini", id="gpt-5-mini/Azure GPT-5 mini"),
    pytest.param("gpt-5-mini", "GPT 5 mini", id="gpt-5-mini/GPT 5 mini"),
    pytest.param("gpt-5-mini", "azure/gpt-5-mini", id="gpt-5-mini/azure-slash"),
    pytest.param("o3-mini", "Azure OpenAI o3-mini", id="o3-mini/Azure OpenAI o3-mini"),
]


@pytest.mark.parametrize("kwargs", PATHS)
@pytest.mark.parametrize(("deployment", "model_name"), DISPLAY_NAME_WITH_MODEL_DEPLOYMENT)
def test_reasoning_deployment_with_display_model_name_omits_temperature(azure, deployment, model_name, kwargs):
    """MODEL_NAME が表示名でも、デプロイ名が推論モデル名なら temperature を送らない（どちらかが推論なら推論）"""
    azure.configure(deployment, model_name=model_name, reject_temperature=True)

    _call(kwargs)

    assert len(azure.sent) == 1
    assert "temperature" not in azure.sent[0]


@pytest.mark.parametrize("kwargs", PATHS)
def test_reasoning_like_deployment_with_non_reasoning_model_name_omits_temperature(azure, kwargs):
    """デプロイ名が推論モデルに見えれば、MODEL_NAME が通常モデルでも temperature を外す側に倒す

    temperature を外して通常モデルに送っても 400 にはならない（決定性が下がるだけ）が、
    推論モデルに temperature=0 を送ると 400 になるため、迷ったら外す。
    """
    azure.configure("o1-team-deploy", model_name="gpt-4o")

    _call(kwargs)

    assert "temperature" not in azure.sent[0]


@pytest.mark.parametrize("kwargs", PATHS)
def test_non_reasoning_model_with_reasoning_like_deployment_sends_temperature_when_explicit_false(azure, kwargs):
    """デプロイ名が推論モデルに見えても、REASONING=false を明示すれば temperature=0 を送る"""
    azure.configure("o1-team-deploy", model_name="gpt-4o", reasoning="false")

    _call(kwargs)

    assert azure.sent[0]["temperature"] == 0


@pytest.mark.parametrize("model_name", [None, "", "   "])
def test_falls_back_to_deployment_name_when_model_name_is_empty(azure, model_name):
    """MODEL_NAME が未設定・空なら、従来どおりデプロイ名で判定する"""
    azure.configure("gpt-5-mini", model_name=model_name)
    _call({})
    assert "temperature" not in azure.sent[-1]

    azure.configure("gpt-4o", model_name=model_name)
    _call({})
    assert azure.sent[-1]["temperature"] == 0


@pytest.mark.parametrize("value", ["true", "1", "TRUE", " on "])
def test_reasoning_override_true_omits_temperature(azure, value):
    """AZURE_CHATCOMPLETION_REASONING=true なら、名前にかかわらず temperature を送らない"""
    azure.configure("kouchou-chat", model_name="gpt-4o", reasoning=value)
    _call({"json_schema": _Answer})
    assert "temperature" not in azure.sent[0]


@pytest.mark.parametrize("value", ["false", "0", "off"])
def test_reasoning_override_false_sends_temperature(azure, value):
    """AZURE_CHATCOMPLETION_REASONING=false なら、名前が推論モデルでも temperature=0 を送る"""
    azure.configure("o3", model_name="o3", reasoning=value)
    _call({"json_schema": _Answer})
    assert azure.sent[0]["temperature"] == 0


@pytest.mark.parametrize("value", ["", "auto", "maybe"])
def test_reasoning_override_auto_or_unknown_uses_names(azure, value):
    """空・auto・解釈できない値は自動判定（MODEL_NAME とデプロイ名）に任せる"""
    azure.configure("kouchou-chat", model_name="gpt-5-mini", reasoning=value)
    _call({})
    assert "temperature" not in azure.sent[0]
