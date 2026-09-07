"""Estimated token costs from the shared server model catalog."""

from src.services.model_catalog import normalize_model, price_for_model, pricing_table


class LLMPricing:
    @staticmethod
    def calculate_cost(provider: str, model: str, token_usage_input: int, token_usage_output: int) -> float | None:
        price = price_for_model(provider, model)
        if price is None:
            return None
        # Aggregate usage cannot identify per-request long-context tiers. Do not
        # present a base-rate estimate when the threshold could have been crossed.
        limit = price.get("max_input_tokens_per_request")
        if limit is not None and token_usage_input > limit:
            return None
        return (token_usage_input * price["input"] + token_usage_output * price["output"]) / 1_000_000

    @staticmethod
    def format_cost(cost: float | None) -> str:
        return "料金不明" if cost is None else f"${cost:.4f}"

    pricing_table = staticmethod(pricing_table)
    _normalize_gemini_model = staticmethod(lambda model: normalize_model("gemini", model))
