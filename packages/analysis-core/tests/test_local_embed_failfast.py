"""Regression tests: request_to_local_llm_embed must fail fast, not silently swap models.

以前は OpenAI 互換のローカルLLM埋め込み呼び出しが失敗すると、別モデル
(sentence-transformers mpnet, 768 次元) へ暗黙に fallback していた。これはバッチ単位で
埋め込み次元を変え、
  - 一部バッチだけ失敗 → 次元が混在し下流 hierarchical_clustering の np.asarray が
    ValueError(inhomogeneous shape) で落ちる（原因が追いにくい）
  - 全バッチ失敗 → 次元は揃うが設定と異なるモデルで silent に完走する（wrong model）
という問題を生む。本テストは「失敗時は別モデルへ swap せず RuntimeError で fail-fast する」
契約を pin する。
"""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from analysis_core.services.llm import request_to_local_llm_embed


def _mock_openai_returning(vectors):
    """OpenAI クライアントのモックを返す。embeddings.create が vectors を返す。"""
    response = SimpleNamespace(data=[SimpleNamespace(embedding=v) for v in vectors])
    client = MagicMock()
    client.embeddings.create.return_value = response
    return MagicMock(return_value=client)


def test_local_llm_embed_returns_vectors_on_success():
    """正常時は OpenAI 互換エンドポイントの埋め込みをそのまま返す。"""
    args = ["a", "b"]
    openai_factory = _mock_openai_returning([[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]])

    with patch("analysis_core.services.llm.OpenAI", openai_factory):
        result = request_to_local_llm_embed(args, "my-embed-model", address="localhost:11434")

    assert result == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]


def test_local_llm_embed_fails_fast_without_swapping_models():
    """エンドポイント失敗時は別モデルへ暗黙 fallback せず RuntimeError で fail-fast する。"""
    args = ["a", "b"]

    client = MagicMock()
    client.embeddings.create.side_effect = RuntimeError("connection refused")
    openai_factory = MagicMock(return_value=client)

    # 旧挙動ならここが呼ばれて mpnet(768次元) に swap していた。呼ばれないことを確認する。
    with (
        patch("analysis_core.services.llm.OpenAI", openai_factory),
        patch("analysis_core.services.llm.request_to_local_embed") as mock_local_embed,
    ):
        with pytest.raises(RuntimeError) as excinfo:
            request_to_local_llm_embed(args, "my-embed-model", address="localhost:11434")

    mock_local_embed.assert_not_called()
    message = str(excinfo.value)
    # 原因が追えるよう、失敗したモデル名と元エラーを含める
    assert "my-embed-model" in message
    assert "connection refused" in message
