import os
from unittest.mock import MagicMock, patch

import openai
import pytest
from broadlistening.pipeline.services.llm import (
    _validate_model,
    request_to_azure_chatcompletion,
    request_to_azure_embed,  # noqa: F401
    request_to_chat_openai,
    request_to_embed,  # noqa: F401
    request_to_openai,
)
from openai import AzureOpenAI  # noqa: F401


class TestLLMService:
    """LLMサービスのテスト"""

    @pytest.fixture
    def mock_openai_response(self):
        """OpenAIのレスポンスをモック化するフィクスチャ"""
        mock_choice = MagicMock()
        mock_choice.message.content = "This is a test response"

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        return mock_response

    @pytest.fixture
    def mock_openai_embedding_response(self):
        """OpenAIの埋め込みレスポンスをモック化するフィクスチャ"""
        mock_item = MagicMock()
        mock_item.embedding = [0.1, 0.2, 0.3]

        mock_response = MagicMock()
        mock_response.data = [mock_item]
        return mock_response

    def test_request_to_openai_success(self, mock_openai_response):
        """request_to_openai: 成功時はレスポンスのコンテンツを返す"""
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, world!"},
        ]

        # openai.chat.completions.createをモック化
        with patch("openai.chat.completions.create", return_value=mock_openai_response):
            response = request_to_openai(messages, model="gpt-4")

        assert response == "This is a test response"

    def test_request_to_openai_rate_limit_error_retry(self):
        """request_to_openai: レート制限エラーが発生した場合は3回までリトライする"""
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, world!"},
        ]

        # 最初の2回はRateLimitErrorを発生させ、3回目は正常なレスポンスを返す
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "This is a test response after retry"
        mock_response.choices = [mock_choice]

        rate_limit_error = openai.RateLimitError(
            message="Rate limit exceeded",
            response=MagicMock(),
            body=MagicMock(),
        )

        # side_effectに複数の値を指定すると、呼び出しごとに順番に返される
        side_effects = [rate_limit_error, rate_limit_error, mock_response]

        with patch("openai.chat.completions.create", side_effect=side_effects):
            # リトライ後に正常なレスポンスが返されることを確認
            response = request_to_openai(messages, model="gpt-4")
            assert response == "This is a test response after retry"

    def test_request_to_openai_rate_limit_error_max_retries(self):
        """request_to_openai: レート制限エラーが4回発生した場合は例外を再発生させる"""
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, world!"},
        ]

        # 4回連続でRateLimitErrorを発生させる
        rate_limit_error = openai.RateLimitError(
            message="Rate limit exceeded",
            response=MagicMock(),
            body=MagicMock(),
        )

        with patch("openai.chat.completions.create", side_effect=[rate_limit_error] * 4):
            # 3回リトライしても失敗するため、最終的に例外が発生する
            with pytest.raises(openai.RateLimitError):
                request_to_openai(messages, model="gpt-4")

    def test_request_to_openai_authentication_error(self):
        """request_to_openai: 認証エラーが発生した場合は例外を再発生させる"""
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, world!"},
        ]

        # openai.chat.completions.createをモック化してAuthenticationErrorを発生させる
        auth_error = openai.AuthenticationError(
            message="Invalid API key",
            response=MagicMock(),
            body=MagicMock(),
        )
        with patch("openai.chat.completions.create", side_effect=auth_error):
            with pytest.raises(openai.AuthenticationError):
                request_to_openai(messages, model="gpt-4")

    def test_request_to_openai_bad_request_error(self):
        """request_to_openai: 不正なリクエストエラーが発生した場合は例外を再発生させる"""
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, world!"},
        ]

        # openai.chat.completions.createをモック化してBadRequestErrorを発生させる
        bad_request_error = openai.BadRequestError(
            message="Bad request",
            response=MagicMock(),
            body=MagicMock(),
        )
        with patch("openai.chat.completions.create", side_effect=bad_request_error):
            with pytest.raises(openai.BadRequestError):
                request_to_openai(messages, model="gpt-4")

    def test_request_to_azure_chatcompletion_success(self, mock_openai_response):
        """request_to_azure_chatcompletion: 成功時はレスポンスのコンテンツを返す"""
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, world!"},
        ]

        # AzureOpenAIクライアントをモック化
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_openai_response

        # 環境変数をモック化
        env_vars = {
            "AZURE_CHATCOMPLETION_ENDPOINT": "https://example.azure.com",
            "AZURE_CHATCOMPLETION_DEPLOYMENT_NAME": "test-deployment",
            "AZURE_CHATCOMPLETION_API_KEY": "test-api-key",
            "AZURE_CHATCOMPLETION_VERSION": "2023-05-15",
        }

        with patch.dict(os.environ, env_vars):
            with patch("broadlistening.pipeline.services.llm.AzureOpenAI", return_value=mock_client):
                response = request_to_azure_chatcompletion(messages)

        assert response == "This is a test response"
        mock_client.chat.completions.create.assert_called_once()

    def test_request_to_azure_chatcompletion_with_json(self, mock_openai_response):
        """request_to_azure_chatcompletion: JSON形式のレスポンスを要求できる"""
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, world!"},
        ]

        # AzureOpenAIクライアントをモック化
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_openai_response

        # 環境変数をモック化
        env_vars = {
            "AZURE_CHATCOMPLETION_ENDPOINT": "https://example.azure.com",
            "AZURE_CHATCOMPLETION_DEPLOYMENT_NAME": "test-deployment",
            "AZURE_CHATCOMPLETION_API_KEY": "test-api-key",
            "AZURE_CHATCOMPLETION_VERSION": "2023-05-15",
        }

        with patch.dict(os.environ, env_vars):
            with patch("broadlistening.pipeline.services.llm.AzureOpenAI", return_value=mock_client):
                response = request_to_azure_chatcompletion(messages, is_json=True)

        assert response == "This is a test response"
        # JSON形式のレスポンスを要求していることを確認
        mock_client.chat.completions.create.assert_called_once()
        args, kwargs = mock_client.chat.completions.create.call_args
        assert kwargs["response_format"] == {"type": "json_object"}

    def test_request_to_azure_chatcompletion_rate_limit_error(self):
        """request_to_azure_chatcompletion: レート制限エラーが発生した場合は例外を再発生させる"""
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, world!"},
        ]

        # AzureOpenAIクライアントをモック化してRateLimitErrorを発生させる
        mock_client = MagicMock()
        rate_limit_error = openai.RateLimitError(
            message="Rate limit exceeded",
            response=MagicMock(),
            body=MagicMock(),
        )
        mock_client.chat.completions.create.side_effect = rate_limit_error

        # 環境変数をモック化
        env_vars = {
            "AZURE_CHATCOMPLETION_ENDPOINT": "https://example.azure.com",
            "AZURE_CHATCOMPLETION_DEPLOYMENT_NAME": "test-deployment",
            "AZURE_CHATCOMPLETION_API_KEY": "test-api-key",
            "AZURE_CHATCOMPLETION_VERSION": "2023-05-15",
        }

        with patch.dict(os.environ, env_vars):
            with patch("broadlistening.pipeline.services.llm.AzureOpenAI", return_value=mock_client):
                with pytest.raises(openai.RateLimitError):
                    request_to_azure_chatcompletion(messages)

    def test_request_to_azure_chatcompletion_rate_limit_error_retry(self):
        """request_to_azure_chatcompletion: レート制限エラーが発生した場合は3回までリトライする"""
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, world!"},
        ]

        # 最初の2回はRateLimitErrorを発生させ、3回目は正常なレスポンスを返す
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "This is a test response after retry"
        mock_response.choices = [mock_choice]

        rate_limit_error = openai.RateLimitError(
            message="Rate limit exceeded",
            response=MagicMock(),
            body=MagicMock(),
        )

        # AzureOpenAIクライアントをモック化
        mock_client = MagicMock()
        # side_effectに複数の値を指定すると、呼び出しごとに順番に返される
        mock_client.chat.completions.create.side_effect = [rate_limit_error, rate_limit_error, mock_response]

        # 環境変数をモック化
        env_vars = {
            "AZURE_CHATCOMPLETION_ENDPOINT": "https://example.azure.com",
            "AZURE_CHATCOMPLETION_DEPLOYMENT_NAME": "test-deployment",
            "AZURE_CHATCOMPLETION_API_KEY": "test-api-key",
            "AZURE_CHATCOMPLETION_VERSION": "2023-05-15",
        }

        with patch.dict(os.environ, env_vars):
            with patch("broadlistening.pipeline.services.llm.AzureOpenAI", return_value=mock_client):
                # リトライ後に正常なレスポンスが返されることを確認
                response = request_to_azure_chatcompletion(messages)
                assert response == "This is a test response after retry"

    def test_request_to_azure_chatcompletion_rate_limit_error_max_retries(self):
        """request_to_azure_chatcompletion: レート制限エラーが4回発生した場合は例外を再発生させる"""
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, world!"},
        ]

        # 4回連続でRateLimitErrorを発生させる
        rate_limit_error = openai.RateLimitError(
            message="Rate limit exceeded",
            response=MagicMock(),
            body=MagicMock(),
        )

        # AzureOpenAIクライアントをモック化
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = [rate_limit_error] * 4

        # 環境変数をモック化
        env_vars = {
            "AZURE_CHATCOMPLETION_ENDPOINT": "https://example.azure.com",
            "AZURE_CHATCOMPLETION_DEPLOYMENT_NAME": "test-deployment",
            "AZURE_CHATCOMPLETION_API_KEY": "test-api-key",
            "AZURE_CHATCOMPLETION_VERSION": "2023-05-15",
        }

        with patch.dict(os.environ, env_vars):
            with patch("broadlistening.pipeline.services.llm.AzureOpenAI", return_value=mock_client):
                # 3回リトライしても失敗するため、最終的に例外が発生する
                with pytest.raises(openai.RateLimitError):
                    request_to_azure_chatcompletion(messages)

    def test_request_to_chat_openai_use_openai(self, mock_openai_response):
        """request_to_chat_openai: USE_AZURE=falseの場合はrequest_to_openaiを使用する"""
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, world!"},
        ]

        # 環境変数をモック化
        env_vars = {"USE_AZURE": "false"}

        # request_to_openaiをモック化
        with patch.dict(os.environ, env_vars):
            with patch(
                "broadlistening.pipeline.services.llm.request_to_openai", return_value="OpenAI response"
            ) as mock_request_to_openai:
                response = request_to_chat_openai(messages, model="gpt-4o")

        assert response == "OpenAI response"
        mock_request_to_openai.assert_called_once_with(messages, "gpt-4o", False)

    def test_request_to_chat_openai_use_azure(self, mock_openai_response):
        """request_to_chat_openai: USE_AZURE=trueの場合はrequest_to_azure_chatcompletionを使用する"""
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, world!"},
        ]

        # 環境変数をモック化
        env_vars = {"USE_AZURE": "true"}

        # request_to_azure_chatcompletionをモック化
        with patch.dict(os.environ, env_vars):
            with patch(
                "broadlistening.pipeline.services.llm.request_to_azure_chatcompletion", return_value="Azure response"
            ) as mock_request_to_azure:
                response = request_to_chat_openai(messages, model="gpt-4o", is_json=True)

        assert response == "Azure response"
        mock_request_to_azure.assert_called_once_with(messages, True)

    def test_validate_model_valid(self):
        """_validate_model: 有効なモデルの場合は例外を発生させない"""
        # 有効なモデル
        _validate_model("text-embedding-3-large")
        _validate_model("text-embedding-3-small")

    def test_validate_model_invalid(self):
        """_validate_model: 無効なモデルの場合はRuntimeErrorを発生させる"""
        # 無効なモデル
        with pytest.raises(RuntimeError) as excinfo:
            _validate_model("invalid-model")
        assert "Invalid embedding model" in str(excinfo.value)
