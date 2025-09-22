import os
from unittest.mock import MagicMock, patch

import openai
import pytest
from broadlistening.pipeline.services.llm import (
    _validate_model,
    request_to_azure_chatcompletion,
    request_to_azure_embed,  # noqa: F401
    request_to_chat_ai,
    request_to_embed,  # noqa: F401
    request_to_openai,
)
from openai import AzureOpenAI  # noqa: F401
from pydantic import BaseModel, Field


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

    @pytest.fixture
    def mock_openai_parse_response(self):
        """OpenAIのパースレスポンスをモック化するフィクスチャ"""
        mock_choice = MagicMock()
        mock_choice.message.content = {"test": "This is a test response"}

        mock_response = MagicMock()
        mock_response.choices = [mock_choice]
        return mock_response

    def test_request_to_openai_success(self, mock_openai_response):
        """request_to_openai: 成功時はレスポンスのコンテンツを返す"""
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, world!"},
        ]

        mock_openai_response.configure_mock(
            **{"usage.prompt_tokens": 10, "usage.completion_tokens": 5, "usage.total_tokens": 15}
        )

        # OpenAIクライアントをモック化
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_openai_response

        with patch("broadlistening.pipeline.services.llm.OpenAI", return_value=mock_client):
            response, token_input, token_output, token_total = request_to_openai(messages, model="gpt-4")

        assert response == "This is a test response"
        assert token_input == 10
        assert token_output == 5
        assert token_total == 15

    def test_request_to_openai_with_json(self, mock_openai_response):
        """request_to_openai: JSON形式のレスポンスを要求できる"""
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, world!"},
        ]

        mock_openai_response.configure_mock(
            **{"usage.prompt_tokens": 10, "usage.completion_tokens": 5, "usage.total_tokens": 15}
        )

        # OpenAIクライアントをモック化
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_openai_response

        with patch("broadlistening.pipeline.services.llm.OpenAI", return_value=mock_client):
            response, token_input, token_output, token_total = request_to_openai(messages, model="gpt-4", is_json=True)

        assert response == "This is a test response"
        assert token_input == 10
        assert token_output == 5
        assert token_total == 15

        # JSON形式のレスポンスを要求していることを確認
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_openai_response

        with patch("broadlistening.pipeline.services.llm.OpenAI", return_value=mock_client):
            request_to_openai(messages, model="gpt-4", is_json=True)
            args, kwargs = mock_client.chat.completions.create.call_args
            assert kwargs["response_format"] == {"type": "json_object"}

    def test_request_to_openai_with_json_schema(self, mock_openai_response):
        """request_to_openai: JSON Schemaを指定できる"""
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, world!"},
        ]

        # JSON Schemaを定義
        json_schema = {
            "type": "json_schema",
            "json_schema": {
                "name": "TestSchema",
                "schema": {
                    "type": "object",
                    "properties": {
                        "test": {"type": "string"},
                    },
                    "required": ["test"],
                },
            },
        }

        mock_openai_response.configure_mock(
            **{"usage.prompt_tokens": 10, "usage.completion_tokens": 5, "usage.total_tokens": 15}
        )

        # OpenAIクライアントをモック化
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_openai_response

        with patch("broadlistening.pipeline.services.llm.OpenAI", return_value=mock_client):
            response, token_input, token_output, token_total = request_to_openai(
                messages, model="gpt-4", json_schema=json_schema
            )

        assert response == "This is a test response"
        assert token_input == 10
        assert token_output == 5
        assert token_total == 15

        # JSON Schemaを指定していることを確認
        args, kwargs = mock_client.chat.completions.create.call_args
        assert kwargs["response_format"] == json_schema

    def test_request_to_openai_with_pydantic_model(self, mock_openai_parse_response):
        """request_to_openai: Pydantic BaseModelを指定できる"""
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, world!"},
        ]

        # テスト用のPydantic BaseModelを定義
        class TestModel(BaseModel):
            test: str = Field(..., description="テスト用フィールド")

        mock_openai_parse_response.configure_mock(
            **{"usage.prompt_tokens": 10, "usage.completion_tokens": 5, "usage.total_tokens": 15}
        )

        # OpenAIクライアントをモック化
        mock_client = MagicMock()
        mock_client.beta.chat.completions.parse.return_value = mock_openai_parse_response

        with patch("broadlistening.pipeline.services.llm.OpenAI", return_value=mock_client):
            response, token_input, token_output, token_total = request_to_openai(
                messages, model="gpt-4", json_schema=TestModel
            )

        assert response == {"test": "This is a test response"}
        assert token_input == 10
        assert token_output == 5
        assert token_total == 15

        # Pydantic BaseModelを指定していることを確認
        args, kwargs = mock_client.beta.chat.completions.parse.call_args
        assert kwargs["response_format"] == TestModel

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
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        mock_response.usage.total_tokens = 15

        rate_limit_error = openai.RateLimitError(
            message="Rate limit exceeded",
            response=MagicMock(),
            body=MagicMock(),
        )

        # side_effectに複数の値を指定すると、呼び出しごとに順番に返される
        side_effects = [rate_limit_error, rate_limit_error, mock_response]

        # OpenAIクライアントをモック化
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = side_effects

        with patch("broadlistening.pipeline.services.llm.OpenAI", return_value=mock_client):
            # リトライ後に正常なレスポンスが返されることを確認
            response, token_input, token_output, token_total = request_to_openai(messages, model="gpt-4")
            assert response == "This is a test response after retry"
            assert token_input == 10
            assert token_output == 5
            assert token_total == 15

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

        # OpenAIクライアントをモック化
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = [rate_limit_error] * 4

        with patch("broadlistening.pipeline.services.llm.OpenAI", return_value=mock_client):
            # 3回リトライしても失敗するため、最終的に例外が発生する
            with pytest.raises(openai.RateLimitError):
                request_to_openai(messages, model="gpt-4")

    def test_request_to_openai_authentication_error(self):
        """request_to_openai: 認証エラーが発生した場合は例外を再発生させる"""
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, world!"},
        ]

        # OpenAIクライアントをモック化してAuthenticationErrorを発生させる
        auth_error = openai.AuthenticationError(
            message="Invalid API key",
            response=MagicMock(),
            body=MagicMock(),
        )

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = auth_error

        with patch("broadlistening.pipeline.services.llm.OpenAI", return_value=mock_client):
            with pytest.raises(openai.AuthenticationError):
                request_to_openai(messages, model="gpt-4")

    def test_request_to_openai_bad_request_error(self):
        """request_to_openai: 不正なリクエストエラーが発生した場合は例外を再発生させる"""
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, world!"},
        ]

        # OpenAIクライアントをモック化してBadRequestErrorを発生させる
        bad_request_error = openai.BadRequestError(
            message="Bad request",
            response=MagicMock(),
            body=MagicMock(),
        )

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = bad_request_error

        with patch("broadlistening.pipeline.services.llm.OpenAI", return_value=mock_client):
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

        mock_openai_response.configure_mock(
            **{"usage.prompt_tokens": 10, "usage.completion_tokens": 5, "usage.total_tokens": 15}
        )

        # 環境変数をモック化
        env_vars = {
            "AZURE_CHATCOMPLETION_ENDPOINT": "https://example.azure.com",
            "AZURE_CHATCOMPLETION_DEPLOYMENT_NAME": "test-deployment",
            "AZURE_CHATCOMPLETION_API_KEY": "test-api-key",
            "AZURE_CHATCOMPLETION_VERSION": "2023-05-15",
        }

        with patch.dict(os.environ, env_vars):
            with patch("broadlistening.pipeline.services.llm.AzureOpenAI", return_value=mock_client):
                response, token_input, token_output, token_total = request_to_azure_chatcompletion(messages)

        assert response == "This is a test response"
        assert token_input == 10
        assert token_output == 5
        assert token_total == 15
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

        mock_openai_response.usage.prompt_tokens = 10
        mock_openai_response.usage.completion_tokens = 5
        mock_openai_response.usage.total_tokens = 15

        # 環境変数をモック化
        env_vars = {
            "AZURE_CHATCOMPLETION_ENDPOINT": "https://example.azure.com",
            "AZURE_CHATCOMPLETION_DEPLOYMENT_NAME": "test-deployment",
            "AZURE_CHATCOMPLETION_API_KEY": "test-api-key",
            "AZURE_CHATCOMPLETION_VERSION": "2023-05-15",
        }

        with patch.dict(os.environ, env_vars):
            with patch("broadlistening.pipeline.services.llm.AzureOpenAI", return_value=mock_client):
                response, token_input, token_output, token_total = request_to_azure_chatcompletion(
                    messages, is_json=True
                )

        assert response == "This is a test response"
        assert token_input == 10
        assert token_output == 5
        assert token_total == 15
        # JSON形式のレスポンスを要求していることを確認
        mock_client.chat.completions.create.assert_called_once()
        args, kwargs = mock_client.chat.completions.create.call_args
        assert kwargs["response_format"] == {"type": "json_object"}

    def test_request_to_azure_chatcompletion_with_json_schema(self, mock_openai_response):
        """request_to_azure_chatcompletion: JSON Schemaを指定できる"""
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, world!"},
        ]

        # AzureOpenAIクライアントをモック化
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = mock_openai_response

        mock_openai_response.usage.prompt_tokens = 10
        mock_openai_response.usage.completion_tokens = 5
        mock_openai_response.usage.total_tokens = 15

        # 環境変数をモック化
        env_vars = {
            "AZURE_CHATCOMPLETION_ENDPOINT": "https://example.azure.com",
            "AZURE_CHATCOMPLETION_DEPLOYMENT_NAME": "test-deployment",
            "AZURE_CHATCOMPLETION_API_KEY": "test-api-key",
            "AZURE_CHATCOMPLETION_VERSION": "2023-05-15",
        }

        # JSON Schemaを定義
        json_schema = {
            "type": "json_schema",
            "json_schema": {
                "name": "TestSchema",
                "schema": {
                    "type": "object",
                    "properties": {
                        "test": {"type": "string"},
                    },
                    "required": ["test"],
                },
            },
        }

        with patch.dict(os.environ, env_vars):
            with patch("broadlistening.pipeline.services.llm.AzureOpenAI", return_value=mock_client):
                response, token_input, token_output, token_total = request_to_azure_chatcompletion(
                    messages, json_schema=json_schema
                )

        assert response == "This is a test response"
        assert token_input == 10
        assert token_output == 5
        assert token_total == 15
        # JSON Schemaを指定していることを確認
        mock_client.chat.completions.create.assert_called_once()
        args, kwargs = mock_client.chat.completions.create.call_args
        assert kwargs["response_format"] == json_schema

    def test_request_to_azure_chatcompletion_with_pydantic_model(self):
        """request_to_azure_chatcompletion: Pydantic BaseModelを指定できる"""
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, world!"},
        ]

        # テスト用のPydantic BaseModelを定義
        class TestModel(BaseModel):
            test: str = Field(..., description="テスト用フィールド")

        # AzureOpenAIクライアントをモック化
        mock_client = MagicMock()
        # beta.chat.completions.parseの戻り値をモック化
        mock_parse_response = MagicMock()
        mock_choice = MagicMock()
        mock_message = MagicMock()
        mock_parsed = MagicMock()
        mock_parsed.model_dump.return_value = {"test": "This is a test response"}
        mock_message.parsed = mock_parsed
        mock_choice.message = mock_message
        mock_parse_response.choices = [mock_choice]
        mock_client.beta.chat.completions.parse.return_value = mock_parse_response

        mock_parse_response.usage.prompt_tokens = 10
        mock_parse_response.usage.completion_tokens = 5
        mock_parse_response.usage.total_tokens = 15

        # 環境変数をモック化
        env_vars = {
            "AZURE_CHATCOMPLETION_ENDPOINT": "https://example.azure.com",
            "AZURE_CHATCOMPLETION_DEPLOYMENT_NAME": "test-deployment",
            "AZURE_CHATCOMPLETION_API_KEY": "test-api-key",
            "AZURE_CHATCOMPLETION_VERSION": "2023-05-15",
        }

        with patch.dict(os.environ, env_vars):
            with patch("broadlistening.pipeline.services.llm.AzureOpenAI", return_value=mock_client):
                response, token_input, token_output, token_total = request_to_azure_chatcompletion(
                    messages, json_schema=TestModel
                )

        assert response == {"test": "This is a test response"}
        assert token_input == 10
        assert token_output == 5
        assert token_total == 15
        # Pydantic BaseModelを指定していることを確認
        mock_client.beta.chat.completions.parse.assert_called_once()
        args, kwargs = mock_client.beta.chat.completions.parse.call_args
        assert kwargs["response_format"] == TestModel

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
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        mock_response.usage.total_tokens = 15

        # usageプロパティを設定
        mock_response.usage = MagicMock()
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 5
        mock_response.usage.total_tokens = 15

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
                response, token_input, token_output, token_total = request_to_azure_chatcompletion(messages)
                assert response == "This is a test response after retry"
                assert token_input == 10
                assert token_output == 5
                assert token_total == 15
                assert mock_client.chat.completions.create.call_count == 3

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
        """request_to_chat_openai: provider=openaiの場合はrequest_to_openaiを使用する"""
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, world!"},
        ]

        # request_to_openaiをモック化
        with patch(
            "broadlistening.pipeline.services.llm.request_to_openai", return_value=("OpenAI response", 50, 50, 100)
        ) as mock_request_to_openai:
            response, token_input, token_output, token_total = request_to_chat_ai(
                messages, model="gpt-4o", provider="openai"
            )

        assert response == "OpenAI response"
        assert token_input == 50
        assert token_output == 50
        assert token_total == 100
        mock_request_to_openai.assert_called_once_with(messages, "gpt-4o", False, None, None)

    def test_request_to_chat_openai_use_azure(self, mock_openai_response):
        """request_to_chat_openai: provider=azureの場合はrequest_to_azure_chatcompletionを使用する"""
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, world!"},
        ]

        # request_to_azure_chatcompletionをモック化
        with patch(
            "broadlistening.pipeline.services.llm.request_to_azure_chatcompletion",
            return_value=("Azure response", 75, 75, 150),
        ) as mock_request_to_azure:
            response, token_input, token_output, token_total = request_to_chat_ai(
                messages, model="gpt-4o", is_json=True, provider="azure"
            )

        assert response == "Azure response"
        assert token_input == 75
        assert token_output == 75
        assert token_total == 150
        mock_request_to_azure.assert_called_once_with(messages, True, None, None)

    def test_request_to_chat_openai_with_json_schema(self, mock_openai_response):
        """request_to_chat_openai: json_schemaパラメータを指定できる"""
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, world!"},
        ]

        # JSON Schemaを定義
        json_schema = {
            "type": "json_schema",
            "json_schema": {
                "name": "TestSchema",
                "schema": {
                    "type": "object",
                    "properties": {
                        "test": {"type": "string"},
                    },
                    "required": ["test"],
                },
            },
        }

        # request_to_openaiをモック化
        with patch(
            "broadlistening.pipeline.services.llm.request_to_openai", return_value=("OpenAI response", 100, 100, 200)
        ) as mock_request_to_openai:
            response, token_input, token_output, token_total = request_to_chat_ai(
                messages, model="gpt-4o", json_schema=json_schema, provider="openai"
            )

        assert response == "OpenAI response"
        assert token_input == 100
        assert token_output == 100
        assert token_total == 200
        mock_request_to_openai.assert_called_once_with(messages, "gpt-4o", False, json_schema, None)

    def test_request_to_chat_openai_with_pydantic_model(self, mock_openai_response):
        """request_to_chat_openai: Pydantic BaseModelを指定できる"""
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, world!"},
        ]

        # テスト用のPydantic BaseModelを定義
        class TestModel(BaseModel):
            test: str = Field(..., description="テスト用フィールド")

        # request_to_openaiをモック化
        with patch(
            "broadlistening.pipeline.services.llm.request_to_openai", return_value=("OpenAI response", 125, 125, 250)
        ) as mock_request_to_openai:
            response, token_input, token_output, token_total = request_to_chat_ai(
                messages, model="gpt-4o", json_schema=TestModel, provider="openai"
            )

        assert response == "OpenAI response"
        assert token_input == 125
        assert token_output == 125
        assert token_total == 250
        mock_request_to_openai.assert_called_once_with(messages, "gpt-4o", False, TestModel, None)

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

    def test_request_to_chat_ai_use_openrouter(self):
        """OpenRouterを使用するテストケース"""
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello!"},
        ]
        model = "openai/gpt-4o-2024-08-06"

        # OpenRouterのクライアントをモック化
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "Hi! How can I help you today?"
        mock_response.choices = [mock_choice]
        mock_response.usage.prompt_tokens = 20
        mock_response.usage.completion_tokens = 10
        mock_response.usage.total_tokens = 30
        mock_client.chat.completions.create.return_value = mock_response

        # 環境変数をモック化
        env_vars = {
            "OPENROUTER_API_KEY": "test-api-key",
        }

        with patch.dict(os.environ, env_vars):
            with patch("broadlistening.pipeline.services.llm.OpenAI", return_value=mock_client):
                response, token_input, token_output, token_total = request_to_chat_ai(
                    messages=messages,
                    model=model,
                    provider="openrouter",
                )

        assert response == "Hi! How can I help you today?"
        assert token_input == 20
        assert token_output == 10
        assert token_total == 30
        mock_client.chat.completions.create.assert_called_once_with(
            model=model,
            messages=messages,
            temperature=0,
            n=1,
            seed=0,
            timeout=30,
        )

    def test_request_to_chat_ai_use_openrouter_without_env(self):
        """OpenRouterの環境変数が設定されていない場合のテスト"""
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello!"},
        ]
        model = "openai/gpt-4o-2024-08-06"

        # 環境変数をクリア
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(RuntimeError) as excinfo:
                request_to_chat_ai(messages=messages, model=model, provider="openrouter")
            assert "OPENROUTER_API_KEY environment variable is not set" in str(excinfo.value)

    def test_request_to_azure_chatcompletion_missing_environment_variables(self):
        """Azure OpenAI: 環境変数が不足している場合はRuntimeErrorを発生させる"""
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello"},
        ]

        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(RuntimeError) as excinfo:
                request_to_azure_chatcompletion(messages)
            error_message = str(excinfo.value)
            assert "Azure OpenAI environment variables not set" in error_message
            assert "AZURE_CHATCOMPLETION_ENDPOINT" in error_message
            assert "AZURE_CHATCOMPLETION_DEPLOYMENT_NAME" in error_message
            assert "AZURE_CHATCOMPLETION_API_KEY" in error_message
            assert "AZURE_CHATCOMPLETION_VERSION" in error_message
            assert "Use AZURE_CHATCOMPLETION_* variables, not AZURE_OPENAI_*" in error_message

    def test_request_to_azure_embed_missing_environment_variables(self):
        """Azure OpenAI embedding: 環境変数が不足している場合はRuntimeErrorを発生させる"""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(RuntimeError) as excinfo:
                request_to_azure_embed(["test text"], "text-embedding-3-large")
            error_message = str(excinfo.value)
            assert "Azure OpenAI embedding environment variables not set" in error_message
            assert "AZURE_EMBEDDING_ENDPOINT" in error_message
            assert "AZURE_EMBEDDING_DEPLOYMENT_NAME" in error_message
            assert "AZURE_EMBEDDING_API_KEY" in error_message
            assert "AZURE_EMBEDDING_VERSION" in error_message
            assert "Use AZURE_EMBEDDING_* variables, not AZURE_OPENAI_*" in error_message

    def test_request_to_chat_ai_use_openrouter_rate_limit(self):
        """OpenRouterのレート制限エラーのテスト"""
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello!"},
        ]
        model = "openai/gpt-4o-2024-08-06"

        # レート制限エラーの場合
        mock_client = MagicMock()
        rate_limit_error = openai.RateLimitError(
            message="Rate limit exceeded",
            response=MagicMock(),
            body=MagicMock(),
        )
        mock_client.chat.completions.create.side_effect = rate_limit_error

        env_vars = {
            "OPENROUTER_API_KEY": "test-api-key",
        }

        with patch.dict(os.environ, env_vars):
            with patch("broadlistening.pipeline.services.llm.OpenAI", return_value=mock_client):
                with pytest.raises(openai.RateLimitError):
                    request_to_chat_ai(messages=messages, model=model, provider="openrouter")
