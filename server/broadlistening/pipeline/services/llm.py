import logging
import os
import threading
from typing import Any

import openai
from dotenv import load_dotenv
from openai import AzureOpenAI, OpenAI
from pydantic import BaseModel
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

DOTENV_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../.env"))
load_dotenv(DOTENV_PATH)

LLM_PROVIDERS = ["openai", "azure", "openrouter", "localllm"]

DEFAULT_PROVIDER = os.getenv("LLM_PROVIDER", "openai").lower()
if DEFAULT_PROVIDER not in LLM_PROVIDERS:
    logging.warning(f"Invalid default LLM provider: {DEFAULT_PROVIDER}, falling back to openai")
    DEFAULT_PROVIDER = "openai"

if DEFAULT_PROVIDER == "azure":
    if not os.getenv("AZURE_CHATCOMPLETION_ENDPOINT"):
        raise RuntimeError("AZURE_CHATCOMPLETION_ENDPOINT environment variable is not set")
    if not os.getenv("AZURE_CHATCOMPLETION_DEPLOYMENT_NAME"):
        raise RuntimeError("AZURE_CHATCOMPLETION_DEPLOYMENT_NAME environment variable is not set")
    if not os.getenv("AZURE_CHATCOMPLETION_API_KEY"):
        raise RuntimeError("AZURE_CHATCOMPLETION_API_KEY environment variable is not set")
    if not os.getenv("AZURE_CHATCOMPLETION_VERSION"):
        raise RuntimeError("AZURE_CHATCOMPLETION_VERSION environment variable is not set")
    if not os.getenv("AZURE_EMBEDDING_ENDPOINT"):
        raise RuntimeError("AZURE_EMBEDDING_ENDPOINT environment variable is not set")
    if not os.getenv("AZURE_EMBEDDING_API_KEY"):
        raise RuntimeError("AZURE_EMBEDDING_API_KEY environment variable is not set")
    if not os.getenv("AZURE_EMBEDDING_VERSION"):
        raise RuntimeError("AZURE_EMBEDDING_VERSION environment variable is not set")
    if not os.getenv("AZURE_EMBEDDING_DEPLOYMENT_NAME"):
        raise RuntimeError("AZURE_EMBEDDING_DEPLOYMENT_NAME environment variable is not set")
elif DEFAULT_PROVIDER == "openrouter":
    if not os.getenv("OPENROUTER_API_KEY"):
        raise RuntimeError("OPENROUTER_API_KEY environment variable is not set")
elif DEFAULT_PROVIDER == "localllm":
    if not os.getenv("LOCALLLM_API_BASE"):
        logging.warning("LOCALLLM_API_BASE not set, using default: http://localhost:1234/v1")


def get_client(provider: str | None = None) -> OpenAI:
    """プロバイダーに基づいてOpenAI APIクライアントを作成する関数"""
    current_provider = provider or DEFAULT_PROVIDER
    if current_provider not in LLM_PROVIDERS:
        logging.warning(f"Invalid provider: {current_provider}, falling back to default")
        current_provider = DEFAULT_PROVIDER
    
    if current_provider == "azure":
        azure_endpoint = os.getenv("AZURE_CHATCOMPLETION_ENDPOINT")
        api_key = os.getenv("AZURE_CHATCOMPLETION_API_KEY")
        api_version = os.getenv("AZURE_CHATCOMPLETION_VERSION")
        
        return AzureOpenAI(
            api_version=api_version,
            azure_endpoint=azure_endpoint,
            api_key=api_key,
        )
    elif current_provider == "openrouter":
        api_key = os.getenv("OPENROUTER_API_KEY")
        api_base = os.getenv("OPENROUTER_API_BASE", "https://openrouter.ai/api/v1")
        
        return OpenAI(
            api_key=api_key,
            base_url=api_base
        )
    elif current_provider == "localllm":
        api_base = os.getenv("LOCALLLM_API_BASE", "http://localhost:1234/v1")
        
        return OpenAI(
            api_key="not-needed",  # LM Studio/ollama は API キーを必要としない
            base_url=api_base
        )
    else:  # default to openai
        return OpenAI()


def get_model_for_provider(provider: str, model: str) -> str:
    """プロバイダーに基づいて適切なモデル名を返す関数"""
    if provider == "azure":
        return os.getenv("AZURE_CHATCOMPLETION_DEPLOYMENT_NAME") or model
    return model


@retry(
    retry=retry_if_exception_type(openai.RateLimitError),
    wait=wait_exponential(multiplier=3, min=3, max=20),
    stop=stop_after_attempt(3),
    reraise=True,
)
def request_to_chat_openai(
    messages: list[dict[str, str]],
    model: str = "gpt-4o",
    is_json: bool = False,
    json_schema: dict[str, Any] | type[BaseModel] | None = None,
    provider: str | None = None,
) -> Any:
    """統合されたチャット完了リクエスト関数"""
    current_provider = provider or DEFAULT_PROVIDER
    if current_provider not in LLM_PROVIDERS:
        logging.warning(f"Invalid provider: {current_provider}, falling back to default")
        current_provider = DEFAULT_PROVIDER
    
    client = get_client(current_provider)
    actual_model = get_model_for_provider(current_provider, model)
    
    provider_name = current_provider.capitalize()
    
    try:
        if isinstance(json_schema, type) and issubclass(json_schema, BaseModel):
            # Use beta.chat.completions.parse for Pydantic BaseModel
            if current_provider == "azure":
                response = client.beta.chat.completions.parse(
                    model=actual_model,
                    messages=messages,
                    temperature=0,
                    n=1,
                    seed=0,
                    response_model=json_schema,
                    timeout=30,
                )
                return response
            else:
                response = client.beta.chat.completions.parse(
                    model=actual_model,
                    messages=messages,
                    temperature=0,
                    n=1,
                    seed=0,
                    response_format=json_schema,
                    timeout=30,
                )
                return response.choices[0].message.content
        
        else:
            response_format = None
            if is_json:
                response_format = {"type": "json_object"}
            if json_schema:  # 両方有効化されていたら、json_schemaを優先
                response_format = json_schema
                
            response = client.chat.completions.create(
                model=actual_model,
                messages=messages,
                temperature=0,
                n=1,
                seed=0,
                response_format=response_format,
                timeout=30,
            )
            
            return response.choices[0].message.content
    except openai.RateLimitError as e:
        logging.warning(f"{provider_name} API rate limit hit: {e}")
        raise
    except openai.AuthenticationError as e:
        logging.error(f"{provider_name} API authentication error: {str(e)}")
        raise
    except openai.BadRequestError as e:
        logging.error(f"{provider_name} API bad request error: {str(e)}")
        raise
    except Exception as e:
        logging.error(f"{provider_name} API error: {str(e)}")
        raise


SUPPORTED_MODELS = {
    "openai": [
        "gpt-4o-mini",
        "gpt-4o",
        "gpt-4-turbo",
        "gpt-3.5-turbo",
    ],
    "azure": [
    ],
    "openrouter": [
        "openai/gpt-4o",
        "openai/gpt-4o-mini",
        "openai/gpt-4o-2024-08-06",
        "openai/gpt-4o-2024-05-13",
        "openai/gpt-4o-mini-2024-07-18",
        "openai/gpt-4o-search-preview",
        "openai/gpt-4o-mini-search-preview",
        "openai/gpt-4-turbo",
        "openai/gpt-4.1",
        "openai/gpt-4.1-mini",
        "openai/gpt-4.1-nano",
        "google/gemini-2.5-pro-preview",
        "google/gemini-2.5-flash-preview",
        "google/gemini-2.5-pro-exp-03-25",
        "anthropic/claude-3-opus",
        "anthropic/claude-3-sonnet",
        "google/gemini-pro-1.5",
        "google/gemini-flash-1.5",
        "mistral/mistral-large",
        "meta/llama-3-70b",
    ],
    "localllm": [
    ]
}

EMBEDDING_MODELS = [
    "text-embedding-3-large",
    "text-embedding-3-small",
]


def _validate_model(model):
    if model not in EMBEDDING_MODELS:
        raise RuntimeError(f"Invalid embedding model: {model}, available models: {EMBEDDING_MODELS}")


def get_embedding_model_for_provider(provider: str, model: str) -> str:
    """プロバイダーに基づいて適切な埋め込みモデル名を返す関数"""
    if provider == "azure":
        return os.getenv("AZURE_EMBEDDING_DEPLOYMENT_NAME") or model
    return model


def get_embedding_client(provider: str | None = None) -> OpenAI:
    """プロバイダーに基づいて埋め込み用のOpenAI APIクライアントを作成する関数"""
    current_provider = provider or DEFAULT_PROVIDER
    if current_provider not in LLM_PROVIDERS:
        logging.warning(f"Invalid provider: {current_provider}, falling back to default")
        current_provider = DEFAULT_PROVIDER
    
    if current_provider == "azure":
        azure_endpoint = os.getenv("AZURE_EMBEDDING_ENDPOINT")
        api_key = os.getenv("AZURE_EMBEDDING_API_KEY")
        api_version = os.getenv("AZURE_EMBEDDING_VERSION")
        
        return AzureOpenAI(
            api_version=api_version,
            azure_endpoint=azure_endpoint,
            api_key=api_key,
        )
    elif current_provider == "openrouter":
        api_key = os.getenv("OPENROUTER_API_KEY")
        api_base = os.getenv("OPENROUTER_API_BASE", "https://openrouter.ai/api/v1")
        
        return OpenAI(
            api_key=api_key,
            base_url=api_base
        )
    elif current_provider == "localllm":
        api_base = os.getenv("LOCALLLM_API_BASE", "http://localhost:1234/v1")
        
        return OpenAI(
            api_key="not-needed",
            base_url=api_base
        )
    else:  # default to openai
        return OpenAI()


def request_to_embed(args, model, is_embedded_at_local=False, provider: str | None = None):
    """統合された埋め込みリクエスト関数"""
    current_provider = provider or DEFAULT_PROVIDER
    if current_provider not in LLM_PROVIDERS:
        logging.warning(f"Invalid provider: {current_provider}, falling back to default")
        current_provider = DEFAULT_PROVIDER
    
    # OpenRouterは埋め込みAPIをサポートしていないため、ローカル埋め込みを使用
    if current_provider == "openrouter" or is_embedded_at_local:
        return request_to_local_embed(args)
    
    if current_provider != "openai":
        _validate_model(model)
    
    client = get_embedding_client(current_provider)
    actual_model = get_embedding_model_for_provider(current_provider, model)
    
    response = client.embeddings.create(input=args, model=actual_model)
    return [item.embedding for item in response.data]


def get_available_models(provider=None):
    """指定されたプロバイダーで利用可能なモデルを取得し、サポートするモデルとマッチングする関数"""
    current_provider = provider or DEFAULT_PROVIDER
    if current_provider not in LLM_PROVIDERS:
        logging.warning(f"Invalid provider: {current_provider}, falling back to default")
        current_provider = DEFAULT_PROVIDER
        
    try:
        client = get_client(current_provider)
        models = client.models.list()
        available_models = [model.id for model in models]
        
        supported_models = SUPPORTED_MODELS.get(current_provider, [])
        matched_models = [model for model in available_models if model in supported_models]
        
        return {
            "available": available_models,
            "supported": matched_models
        }
    except Exception as e:
        logging.error(f"Error getting models for provider {current_provider}: {str(e)}")
        return {
            "available": [],
            "supported": []
        }


__local_emb_model = None
__local_emb_model_loading_lock = threading.Lock()


def request_to_local_embed(args):
    global __local_emb_model
    # memo: モデルを遅延ロード＆キャッシュするために、グローバル変数を使用

    with __local_emb_model_loading_lock:
        # memo: スレッドセーフにするためにロックを使用
        if __local_emb_model is None:
            from sentence_transformers import SentenceTransformer

            model_name = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
            __local_emb_model = SentenceTransformer(model_name)

    result = __local_emb_model.encode(args)
    return result.tolist()


def _test():
    # messages = [
    #     {"role": "system", "content": "英訳せよ"},
    #     {"role": "user", "content": "これはテストです"},
    # ]
    # response = request_to_chat_openai(messages=messages, model="gpt-4o", is_json=False)
    # print(response)
    print(request_to_embed("Hello", "text-embedding-3-large", is_embedded_at_local=False))


def _local_emb_test():
    data = [
        # 料理関連のグループ
        "トマトソースのパスタを作るのが好きです",
        "私はイタリアンの料理が得意です",
        "スパゲッティカルボナーラは簡単においしく作れます",
        # 天気関連のグループ
        "今日は晴れて気持ちがいい天気です",
        "明日の天気予報では雨が降るようです",
        "週末は天気が良くなりそうで外出するのに最適です",
        # 技術関連のグループ
        "新しいスマートフォンは処理速度が速くなりました",
        "最新のノートパソコンはバッテリー持ちが良いです",
        "ワイヤレスイヤホンの音質が向上しています",
        # ランダムなトピック（相関が低いはず）
        "猫は可愛い動物です",
        "チャーハンは簡単に作れる料理です",
        "図書館で本を借りてきました",
    ]
    emb = request_to_local_embed(data)
    print(emb)

    # コサイン類似度行列の出力
    from sklearn.metrics.pairwise import cosine_similarity

    cos_sim = cosine_similarity(emb)
    print(cos_sim)


def _jsonschema_test():
    # JSON schema request example
    response_format = {
        "type": "json_schema",
        "json_schema": {
            "name": "TranslationResponseModel",
            "schema": {
                "type": "object",
                "properties": {
                    "translation": {"type": "string", "description": "英訳結果"},
                    "politeness": {"type": "string", "description": "丁寧さのレベル（例: casual, polite, honorific）"},
                },
                "required": ["translation", "politeness"],
            },
        },
    }

    messages = [
        {
            "role": "system",
            "content": "あなたは翻訳者です。日本語を英語に翻訳してください。翻訳と丁寧さのレベルをJSON形式で返してください。",
        },
        {"role": "user", "content": "これは素晴らしい日です。"},
    ]

    response = request_to_chat_openai(messages=messages, model="gpt-4o", json_schema=response_format)
    print("JSON Schema response example:")
    print(response)


def _basemodel_test():
    # pydanticのBaseModelを使ってOpenAI APIにスキーマを指定してリクエストするテスト
    from pydantic import BaseModel, Field

    class CalendarEvent(BaseModel):
        name: str = Field(..., description="イベント名")
        date: str = Field(..., description="日付")
        participants: list[str] = Field(..., description="参加者")

    messages = [
        {"role": "system", "content": "Extract the event information."},
        {"role": "user", "content": "Alice and Bob are going to a science fair on Friday."},
    ]

    response = request_to_chat_openai(messages=messages, model="gpt-4o", json_schema=CalendarEvent)

    print("Pydantic(BaseModel) schema response example:")
    print(response)


if __name__ == "__main__":
    # _test()
    # _test()
    # _jsonschema_test()
    # _basemodel_test()
    # _local_emb_test()
    pass
