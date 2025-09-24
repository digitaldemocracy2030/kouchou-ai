import pytest

from src.services.llm_pricing import LLMPricing


class TestLLMPricing:
    """LLMPricingサービスのテスト"""

    def test_calculate_cost_openai_gpt4o_mini(self):
        """OpenAIのGPT-4o-miniモデルの料金計算が正しく行われる"""
        provider = "openai"
        model = "gpt-4o-mini"
        token_usage_input = 1_000_000  # 1M tokens
        token_usage_output = 500_000  # 0.5M tokens

        expected_cost = 0.45

        cost = LLMPricing.calculate_cost(provider, model, token_usage_input, token_usage_output)
        assert cost == pytest.approx(expected_cost)

    def test_calculate_cost_openai_gpt4o(self):
        """OpenAIのGPT-4oモデルの料金計算が正しく行われる"""
        provider = "openai"
        model = "gpt-4o"
        token_usage_input = 1_000_000  # 1M tokens
        token_usage_output = 500_000  # 0.5M tokens

        expected_cost = 7.50

        cost = LLMPricing.calculate_cost(provider, model, token_usage_input, token_usage_output)
        assert cost == pytest.approx(expected_cost)

    def test_calculate_cost_openai_o3_mini(self):
        """OpenAIのo3-miniモデルの料金計算が正しく行われる"""
        provider = "openai"
        model = "o3-mini"
        token_usage_input = 1_000_000  # 1M tokens
        token_usage_output = 500_000  # 0.5M tokens

        expected_cost = 3.30

        cost = LLMPricing.calculate_cost(provider, model, token_usage_input, token_usage_output)
        assert cost == pytest.approx(expected_cost)

    def test_calculate_cost_azure_gpt4o_mini(self):
        """AzureのGPT-4o-miniモデルの料金計算が正しく行われる"""
        provider = "azure"
        model = "gpt-4o-mini"
        token_usage_input = 1_000_000  # 1M tokens
        token_usage_output = 500_000  # 0.5M tokens

        expected_cost = 0.45

        cost = LLMPricing.calculate_cost(provider, model, token_usage_input, token_usage_output)
        assert cost == pytest.approx(expected_cost)

    def test_calculate_cost_openrouter_gpt4o(self):
        """OpenRouterのGPT-4oモデルの料金計算が正しく行われる"""
        provider = "openrouter"
        model = "openai/gpt-4o-2024-08-06"
        token_usage_input = 1_000_000  # 1M tokens
        token_usage_output = 500_000  # 0.5M tokens

        expected_cost = 7.50

        cost = LLMPricing.calculate_cost(provider, model, token_usage_input, token_usage_output)
        assert cost == pytest.approx(expected_cost)

    def test_calculate_cost_gemini_flash(self):
        """Geminiのgemini-1.5-flashモデルの料金計算が正しく行われる"""
        provider = "gemini"
        model = "gemini-1.5-flash"
        token_usage_input = 1_000_000  # 1M tokens
        token_usage_output = 500_000  # 0.5M tokens

        expected_cost = 0.875

        cost = LLMPricing.calculate_cost(provider, model, token_usage_input, token_usage_output)
        assert cost == pytest.approx(expected_cost)

    def test_calculate_cost_unknown_provider(self):
        """不明なプロバイダーの場合は0"""
        provider = "unknown_provider"
        model = "gpt-4o-mini"
        token_usage_input = 1_000_000  # 1M tokens
        token_usage_output = 500_000  # 0.5M tokens

        expected_cost = 0

        cost = LLMPricing.calculate_cost(provider, model, token_usage_input, token_usage_output)
        assert cost == pytest.approx(expected_cost)

    def test_calculate_cost_unknown_model(self):
        """不明なモデルの場合は0"""
        provider = "openai"
        model = "unknown_model"
        token_usage_input = 1_000_000  # 1M tokens
        token_usage_output = 500_000  # 0.5M tokens

        expected_cost = 0

        cost = LLMPricing.calculate_cost(provider, model, token_usage_input, token_usage_output)
        assert cost == pytest.approx(expected_cost)

    def test_calculate_cost_small_tokens(self):
        """少量のトークンでも正しく計算される"""
        provider = "openai"
        model = "gpt-4o-mini"
        token_usage_input = 1000  # 1K tokens
        token_usage_output = 500  # 0.5K tokens

        expected_cost = 0.00045

        cost = LLMPricing.calculate_cost(provider, model, token_usage_input, token_usage_output)
        assert cost == pytest.approx(expected_cost)

    def test_calculate_cost_zero_tokens(self):
        """トークン使用量が0の場合は0が返される"""
        provider = "openai"
        model = "gpt-4o-mini"
        token_usage_input = 0
        token_usage_output = 0

        expected_cost = 0.0

        cost = LLMPricing.calculate_cost(provider, model, token_usage_input, token_usage_output)
        assert cost == pytest.approx(expected_cost)

    def test_format_cost(self):
        """コストが正しくフォーマットされる"""
        cost = 1.2345
        expected_format = "$1.2345"

        formatted_cost = LLMPricing.format_cost(cost)
        assert formatted_cost == expected_format

    def test_format_cost_small_value(self):
        """小さな値のコストが正しくフォーマットされる"""
        cost = 0.0001
        expected_format = "$0.0001"

        formatted_cost = LLMPricing.format_cost(cost)
        assert formatted_cost == expected_format

    def test_format_cost_zero(self):
        """0のコストが正しくフォーマットされる"""
        cost = 0.0
        expected_format = "$0.0000"

        formatted_cost = LLMPricing.format_cost(cost)
        assert formatted_cost == expected_format
