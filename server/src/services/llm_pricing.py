import re

"""
LLMモデルの価格計算サービス
"""
class LLMPricing:
    """LLMモデルの価格計算クラス"""
    DEFAULT_PRICE = {"input": 0, "output": 0}  # 不明なモデルは 0 = 情報なし

    PRICING: dict[str, dict[str, dict[str, float]]] = {
        "openai": {
            "gpt-4o-mini": {"input": 0.15, "output": 0.60},
            "gpt-4o": {"input": 2.50, "output": 10.00},
            "o3-mini": {"input": 1.10, "output": 4.40},
        },
        "azure": {
            "gpt-4o-mini": {"input": 0.15, "output": 0.60},
            "gpt-4o": {"input": 2.50, "output": 10.00},
            "o3-mini": {"input": 1.10, "output": 4.40},
        },
        "openrouter": {
            "openai/gpt-4o-mini-2024-07-18": {"input": 0.15, "output": 0.60},
            "openai/gpt-4o-2024-08-06": {"input": 2.50, "output": 10.00},
            "google/gemini-2.5-pro-preview": {"input": 1.25, "output": 10.00},
        },
        "gemini": {
            "gemini-2.5-flash": {"input": 0.35, "output": 1.05},
            "gemini-1.5-flash": {"input": 0.35, "output": 1.05},
            "gemini-1.5-pro": {"input": 3.50, "output": 10.50},
            "gemini-2.5-pro-preview": DEFAULT_PRICE,
        },
    }

    @classmethod
    def calculate_cost(cls, provider: str, model: str, token_usage_input: int, token_usage_output: int) -> float:
        """
        トークン使用量から推定コストを計算する

        Args:
            provider: LLMプロバイダー名
            model: モデル名
            token_usage_input: 入力トークン使用量
            token_usage_output: 出力トークン使用量

        Returns:
            float: 推定コスト（USD）
        """
        if provider not in cls.PRICING:
            return cls._calculate_with_price(cls.DEFAULT_PRICE, token_usage_input, token_usage_output)

        if model not in cls.PRICING[provider]:
            return cls._calculate_with_price(cls.DEFAULT_PRICE, token_usage_input, token_usage_output)

        model_key = (model or "").strip()
        if provider == "gemini":
            model_key = cls._normalize_gemini_model(model_key)
        
        price = cls.PRICING[provider][model_key]
        return cls._calculate_with_price(price, token_usage_input, token_usage_output)

    @staticmethod
    def _calculate_with_price(price: dict[str, float], token_usage_input: int, token_usage_output: int) -> float:
        """
        価格情報とトークン使用量から推定コストを計算する

        Args:
            price: 価格情報（inputとoutputの価格）
            token_usage_input: 入力トークン使用量
            token_usage_output: 出力トークン使用量

        Returns:
            float: 推定コスト（USD）
        """
        input_cost = (token_usage_input / 1_000_000) * price["input"]
        output_cost = (token_usage_output / 1_000_000) * price["output"]
        total_cost = input_cost + output_cost
        return total_cost

    @classmethod
    def format_cost(cls, cost: float) -> str:
        """
        コストを表示用にフォーマットする

        Args:
            cost: コスト値

        Returns:
            str: フォーマットされたコスト文字列
        """
        return f"${cost:.4f}"
    
    _GEMINI_SYNONYMS = {
        "gemini-pro": "gemini-1.5-pro",
        "gemini-flash": "gemini-1.5-flash",
    }
    
    @staticmethod
    def _normalize_gemini_model(model: str) -> str:
        """Geminiのモデル名だけを baseModelId に正規化"""
        m = (model or "").strip().lower()

        # publishers/google/models/... or models/... を吸収
        if "models/" in m:
            m = m.split("models/")[-1]
        # それでもスラッシュが残っていれば最後のセグメントを採用
        if "/" in m:
            m = m.split("/")[-1]

        # 末尾のバージョン/日付サフィックスを除去（-001, -06-05, -20240605 など）
        m = re.sub(r"-(\d{3})$", "", m)                 # -001
        m = re.sub(r"-(\d{2}-\d{2}|\d{8})$", "", m)     # -06-05 / -20240605

        # 旧称の吸収
        m = LLMPricing._GEMINI_SYNONYMS.get(m, m)
        return m
