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

    def test_malformed_address_falls_back_to_default(self) -> None:
        # "host:not-a-port" → int() raises → warn + fallback to default Ollama
        assert _resolve_local_llm_base_url("localhost:not-a-port") == "http://localhost:11434/v1"
