"""Gemini provider: token accounting."""

import types
from unittest.mock import MagicMock, patch

from analysis_core.services import llm


class RateLimitError(Exception):
    def __init__(self, message: str = "Resource exhausted"):
        super().__init__(message)
        self.code = 429


def _genai_with_client(models):
    client = MagicMock()
    client.models = models
    return types.SimpleNamespace(Client=MagicMock(return_value=client))


def test_chat_output_tokens_include_thinking_tokens(monkeypatch):
    """gemini-2.5 系の thinking トークンは出力単価で課金されるので出力トークンに含める。"""
    models = MagicMock()
    models.generate_content.return_value = types.SimpleNamespace(
        text="ok",
        candidates=None,
        prompt_feedback=None,
        usage_metadata=types.SimpleNamespace(
            prompt_token_count=20, candidates_token_count=10, thoughts_token_count=70, total_token_count=100
        ),
    )
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    with (
        patch.object(llm, "genai", _genai_with_client(models)),
        patch.object(llm, "genai_errors", types.SimpleNamespace(ClientError=RateLimitError, ServerError=OSError)),
    ):
        _, token_input, token_output, token_total = llm.request_to_gemini_chatcompletion(
            [{"role": "user", "content": "hi"}]
        )
    assert (token_input, token_output, token_total) == (20, 80, 100)
    assert token_input + token_output == token_total


def test_chat_output_tokens_without_thinking(monkeypatch):
    models = MagicMock()
    models.generate_content.return_value = types.SimpleNamespace(
        text="ok",
        candidates=None,
        prompt_feedback=None,
        usage_metadata=types.SimpleNamespace(
            prompt_token_count=20, candidates_token_count=10, thoughts_token_count=None, total_token_count=30
        ),
    )
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    with (
        patch.object(llm, "genai", _genai_with_client(models)),
        patch.object(llm, "genai_errors", types.SimpleNamespace(ClientError=RateLimitError, ServerError=OSError)),
    ):
        _, token_input, token_output, token_total = llm.request_to_gemini_chatcompletion(
            [{"role": "user", "content": "hi"}]
        )
    assert (token_input, token_output, token_total) == (20, 10, 30)
