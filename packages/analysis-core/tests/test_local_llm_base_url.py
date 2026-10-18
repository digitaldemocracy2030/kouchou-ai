"""Tests for `_resolve_local_llm_base_url` helper.

The helper backs `request_to_local_llm` / `request_to_local_llm_embed`. It
must accept both the historic Ollama / LM Studio `"host:port"` form and a
new full-URL form (e.g. a corporate HTTPS OpenAI-compatible gateway) without
breaking the default.
"""

import pytest

from analysis_core.services.llm import _resolve_local_llm_base_url


class TestResolveLocalLlmBaseUrl:
    @pytest.mark.parametrize(
        ("address", "expected"),
        [
            # historic Ollama / LM Studio form
            ("localhost:11434", "http://localhost:11434/v1"),
            ("127.0.0.1:1234", "http://127.0.0.1:1234/v1"),
            ("192.168.1.5:8080", "http://192.168.1.5:8080/v1"),
            # bare host without port → falls back to Ollama default port
            ("localhost", "http://localhost:11434/v1"),
            # trailing slash on host:port form is accepted
            ("ollama:11434/", "http://ollama:11434/v1"),
            # bracketed IPv6 literal
            ("[::1]:1234", "http://[::1]:1234/v1"),
            # full URL form: corporate HTTPS endpoint without explicit port
            ("https://my-gateway.example.com", "https://my-gateway.example.com/v1"),
            # full URL with explicit port
            ("https://my-gateway.example.com:8443", "https://my-gateway.example.com:8443/v1"),
            # full URL already ending in /v1 → unchanged
            ("https://my-gateway.example.com/v1", "https://my-gateway.example.com/v1"),
            # trailing slash trimmed before checking suffix
            ("https://my-gateway.example.com/v1/", "https://my-gateway.example.com/v1"),
            # full URL with non-/v1 prefix path (gateway routing) → /v1 appended
            ("http://my-gateway:8000/openai", "http://my-gateway:8000/openai/v1"),
            # http (non-tls) full URL works too
            ("http://my-gateway.example.com", "http://my-gateway.example.com/v1"),
        ],
    )
    def test_resolves_address_to_base_url(self, address: str, expected: str) -> None:
        assert _resolve_local_llm_base_url(address) == expected

    @pytest.mark.parametrize("address", ["localhost:not-a-port", "::1:11434", "host:1234/extra", ""])
    def test_malformed_address_is_rejected(self, address: str) -> None:
        # 黙って localhost:11434 に差し替えると、別のサーバーに接続したまま完走しうる
        with pytest.raises(ValueError, match="local LLM address"):
            _resolve_local_llm_base_url(address)
