"""Gemini embeddings: batching and rate limit handling."""

import types
from unittest.mock import MagicMock, patch

import pytest

from analysis_core.services import llm


class RateLimitError(Exception):
    def __init__(self, message: str = "Resource exhausted"):
        super().__init__(message)
        self.code = 429


def _genai_with_client(models):
    client = MagicMock()
    client.models = models
    return types.SimpleNamespace(Client=MagicMock(return_value=client))


def _embed_response(texts):
    return types.SimpleNamespace(embeddings=[types.SimpleNamespace(values=[float(len(t)), 0.0]) for t in texts])


def test_embed_sends_texts_in_batches(monkeypatch):
    """1 テキスト 1 リクエストの逐次送信ではなく、API の上限件数ごとにまとめて送る。"""
    models = MagicMock()
    models.embed_content.side_effect = lambda model, contents: _embed_response(contents)
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    texts = ["x" * (i % 7 + 1) for i in range(250)]
    with patch.object(llm, "genai", _genai_with_client(models)):
        embeds = llm.request_to_gemini_embed(texts, "gemini-embedding-001")
    assert embeds == [[float(len(t)), 0.0] for t in texts]
    sizes = [len(call.kwargs["contents"]) for call in models.embed_content.call_args_list]
    assert sizes == [100, 100, 50]


def test_embed_retries_rate_limit_with_backoff(monkeypatch):
    """429 は chat 経路と同様に指数バックオフで再試行し、埋め込みステップ全体を落とさない。"""
    models = MagicMock()
    models.embed_content.side_effect = [RateLimitError(), RateLimitError(), _embed_response(["a", "bb"])]
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    sleeps = []
    with (
        patch.object(llm, "genai", _genai_with_client(models)),
        patch.object(llm.time, "sleep", sleeps.append),
    ):
        embeds = llm.request_to_gemini_embed(["a", "bb"], "gemini-embedding-001")
    assert embeds == [[1.0, 0.0], [2.0, 0.0]]
    assert models.embed_content.call_count == 3
    assert len(sleeps) == 2


def test_embed_gives_up_after_repeated_rate_limit(monkeypatch):
    models = MagicMock()
    models.embed_content.side_effect = RateLimitError()
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    with (
        patch.object(llm, "genai", _genai_with_client(models)),
        patch.object(llm.time, "sleep", lambda _: None),
    ):
        with pytest.raises(RuntimeError, match="rate limit"):
            llm.request_to_gemini_embed(["a"], "gemini-embedding-001")


def test_embed_does_not_retry_other_errors(monkeypatch):
    class BadRequest(Exception):
        code = 400

    models = MagicMock()
    models.embed_content.side_effect = BadRequest("bad")
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    with patch.object(llm, "genai", _genai_with_client(models)):
        with pytest.raises(BadRequest):
            llm.request_to_gemini_embed(["a"], "gemini-embedding-001")
    assert models.embed_content.call_count == 1


def test_embed_rejects_response_count_mismatch(monkeypatch):
    models = MagicMock()
    models.embed_content.return_value = _embed_response(["only one"])
    monkeypatch.setenv("GEMINI_API_KEY", "k")
    with patch.object(llm, "genai", _genai_with_client(models)):
        with pytest.raises(RuntimeError, match="2"):
            llm.request_to_gemini_embed(["a", "b"], "gemini-embedding-001")
