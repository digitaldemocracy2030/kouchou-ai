"""provider=local で LOCAL_LLM_API_KEY を付ける接続先の判定のテスト

LOCAL_LLM_API_KEY は認証付きの OpenAI 互換ゲートウェイ向けの鍵。管理画面で入力途中のアドレスや
打ち間違えたアドレスへ送らないよう、LOCAL_LLM_ALLOWED_BASE_URLS に書いた接続先と一致する時だけ付ける。
許可リストが空なら、従来どおりどの接続先にも付ける（既存の運用を壊さない互換動作）。
外部には接続しない（OpenAI クライアントを差し替える）。
"""

from unittest.mock import MagicMock, patch

import pytest

from analysis_core.services import llm

NO_KEY = "not-needed"


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv("LOCAL_LLM_API_KEY", raising=False)
    monkeypatch.delenv("LOCAL_LLM_ALLOWED_BASE_URLS", raising=False)


def _chat_api_key(address: str) -> str:
    client = MagicMock()
    client.chat.completions.create.return_value = MagicMock(
        usage=None, choices=[MagicMock(message=MagicMock(content="ok"))]
    )
    with patch.object(llm, "OpenAI", return_value=client) as openai_cls:
        llm.request_to_local_llm([{"role": "user", "content": "hi"}], "llama3", address=address)
    return openai_cls.call_args.kwargs["api_key"]


def _embed_api_key(address: str) -> str:
    client = MagicMock()
    client.embeddings.create.return_value = MagicMock(data=[MagicMock(embedding=[0.1, 0.2])])
    with patch.object(llm, "OpenAI", return_value=client) as openai_cls:
        llm.request_to_local_llm_embed(["hi"], "nomic-embed-text", address=address)
    return openai_cls.call_args.kwargs["api_key"]


@pytest.mark.parametrize("send", [_chat_api_key, _embed_api_key], ids=["chat", "embed"])
class TestLocalLlmApiKeyAllowlist:
    def test_without_key_sends_placeholder(self, send):
        assert send("https://gateway.example.com") == NO_KEY

    def test_empty_allowlist_keeps_compatible_behavior(self, monkeypatch, send):
        monkeypatch.setenv("LOCAL_LLM_API_KEY", "gateway-token")
        assert send("https://gateway.example.com") == "gateway-token"
        assert send("ollama:11434") == "gateway-token"

    @pytest.mark.parametrize(
        "address",
        [
            "https://gateway.example.com",
            "https://gateway.example.com/",
            "https://gateway.example.com/v1",
            "https://GATEWAY.example.com:443",
            "HTTPS://gateway.example.com",
        ],
    )
    def test_allowed_base_url_gets_key(self, monkeypatch, send, address):
        monkeypatch.setenv("LOCAL_LLM_API_KEY", "gateway-token")
        monkeypatch.setenv("LOCAL_LLM_ALLOWED_BASE_URLS", "https://gateway.example.com")
        assert send(address) == "gateway-token"

    @pytest.mark.parametrize(
        "address",
        [
            # 入力途中・打ち間違いのアドレス
            "https://gateway.example.co",
            "https://gateway.example.com.evil.test",
            "https://gateway.exampl.com",
            # スキーム・ポート・パスが違う
            "http://gateway.example.com",
            "https://gateway.example.com:8443",
            "https://gateway.example.com/other",
            # host:port 形式
            "gateway.example.com",
            "ollama:11434",
        ],
    )
    def test_other_base_url_does_not_get_key(self, monkeypatch, send, address):
        monkeypatch.setenv("LOCAL_LLM_API_KEY", "gateway-token")
        monkeypatch.setenv("LOCAL_LLM_ALLOWED_BASE_URLS", "https://gateway.example.com")
        assert send(address) == NO_KEY

    def test_allowlist_accepts_host_port_form_and_multiple_entries(self, monkeypatch, send):
        monkeypatch.setenv("LOCAL_LLM_API_KEY", "gateway-token")
        monkeypatch.setenv("LOCAL_LLM_ALLOWED_BASE_URLS", " ollama:11434 , https://gateway.example.com/openai ")
        assert send("ollama") == "gateway-token"
        assert send("http://ollama:11434/v1") == "gateway-token"
        assert send("https://gateway.example.com/openai/v1") == "gateway-token"
        assert send("ollama:11435") == NO_KEY
        assert send("https://gateway.example.com") == NO_KEY


def test_invalid_allowlist_entry_is_ignored(monkeypatch, caplog):
    monkeypatch.setenv("LOCAL_LLM_API_KEY", "gateway-token")
    monkeypatch.setenv("LOCAL_LLM_ALLOWED_BASE_URLS", "gateway.example.com:abc,https://gateway.example.com")
    assert llm.resolve_local_llm_api_key("https://gateway.example.com/v1") == "gateway-token"
    assert llm.resolve_local_llm_api_key("http://gateway.example.com:11434/v1") == NO_KEY
    assert "LOCAL_LLM_ALLOWED_BASE_URLS" in caplog.text


def test_invalid_allowlist_only_does_not_fall_back_to_any_url(monkeypatch):
    """許可リストに書いたのに全部読めない場合は、空（互換動作）扱いにせず、どこにも付けない"""
    monkeypatch.setenv("LOCAL_LLM_API_KEY", "gateway-token")
    monkeypatch.setenv("LOCAL_LLM_ALLOWED_BASE_URLS", "gateway.example.com:abc")
    assert llm.resolve_local_llm_api_key("https://gateway.example.com/v1") == NO_KEY


def test_key_value_is_not_logged(monkeypatch, caplog):
    monkeypatch.setenv("LOCAL_LLM_API_KEY", "gateway-token")
    monkeypatch.setenv("LOCAL_LLM_ALLOWED_BASE_URLS", "https://gateway.example.com")
    llm.resolve_local_llm_api_key("https://gateway.example.co/v1")
    assert "gateway-token" not in caplog.text
