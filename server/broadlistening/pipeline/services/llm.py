import logging
import os
import threading

import openai
from dotenv import load_dotenv
from openai import AzureOpenAI, OpenAI
from pydantic import BaseModel
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

DOTENV_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../.env"))
load_dotenv(DOTENV_PATH)

# サポートされているLLMプロバイダーのリスト
DEFAULT_PROVIDER = os.getenv("DEFAULT_LLM_PROVIDER", "openai")
LLM_PROVIDERS = [p.strip() for p in os.getenv(
    "LLM_PROVIDERS",
    "openai,azure,openrouter,local"
).split(",")]

# check env
use_azure = os.getenv("USE_AZURE", "false").lower()
if use_azure == "true":
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


@retry(
    retry=retry_if_exception_type(openai.RateLimitError),
    wait=wait_exponential(multiplier=3, min=3, max=20),
    stop=stop_after_attempt(3),
    reraise=True,
)
def request_to_openai(
    messages: list[dict],
    model: str = "gpt-4",
    is_json: bool = False,
    json_schema: dict | type[BaseModel] | None = None,
) -> str:
    openai.api_type = "openai"

    try:
        if isinstance(json_schema, type) and issubclass(json_schema, BaseModel):
            response = openai.beta.chat.completions.parse(
                model=model,
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
            if json_schema:
                response_format = json_schema
            payload = {
                "model": model,
                "messages": messages,
                "temperature": 0,
                "n": 1,
                "seed": 0,
                "timeout": 30,
            }
            if response_format:
                payload["response_format"] = response_format
            response = openai.chat.completions.create(**payload)
            return response.choices[0].message.content
    except openai.RateLimitError as e:
        logging.warning(f"[OpenAI][RateLimit] model={model}, error={e}, messages={messages}")
        raise
    except openai.AuthenticationError as e:
        logging.error(f"[OpenAI][AuthError] model={model}, error={str(e)}, messages={messages}")
        raise
    except openai.BadRequestError as e:
        logging.error(f"[OpenAI][BadRequest] model={model}, error={str(e)}, messages={messages}")
        raise


@retry(
    retry=retry_if_exception_type(openai.RateLimitError),
    wait=wait_exponential(multiplier=1, min=2, max=20),
    stop=stop_after_attempt(3),
    reraise=True,
)
def request_to_azure_chatcompletion(
    messages: list[dict],
    is_json: bool = False,
    json_schema: dict | type[BaseModel] | None = None,
) -> str:
    azure_endpoint = os.getenv("AZURE_CHATCOMPLETION_ENDPOINT")
    deployment = os.getenv("AZURE_CHATCOMPLETION_DEPLOYMENT_NAME")
    api_key = os.getenv("AZURE_CHATCOMPLETION_API_KEY")
    api_version = os.getenv("AZURE_CHATCOMPLETION_VERSION")

    client = AzureOpenAI(
        api_version=api_version,
        azure_endpoint=azure_endpoint,
        api_key=api_key,
    )
    # Set response format based on parameters

    try:
        if isinstance(json_schema, type) and issubclass(json_schema, BaseModel):
            # Use beta.chat.completions.create for Pydantic BaseModel (Azure)
            response = client.beta.chat.completions.parse(
                model=deployment,
                messages=messages,
                temperature=0,
                n=1,
                seed=0,
                response_format=json_schema,
                timeout=30,
            )
            return response.choices[0].message.parsed.model_dump()
        else:
            response_format = None
            if is_json:
                response_format = {"type": "json_object"}
            if json_schema:  # 両方有効化されていたら、json_schemaを優先
                response_format = json_schema

            payload = {
                "model": deployment,
                "messages": messages,
                "temperature": 0,
                "n": 1,
                "seed": 0,
                "timeout": 30,
            }
            if response_format:
                payload["response_format"] = response_format

            response = client.chat.completions.create(**payload)

            return response.choices[0].message.content
    except openai.RateLimitError as e:
        logging.warning(f"OpenAI API rate limit hit: {e}")
        raise
    except openai.AuthenticationError as e:
        logging.error(f"OpenAI API authentication error: {str(e)}")
        raise
    except openai.BadRequestError as e:
        logging.error(f"OpenAI API bad request error: {str(e)}")
        raise


def request_to_local_llm(
    messages: list[dict],
    model: str,
    is_json: bool = False,
    json_schema: dict | type[BaseModel] | None = None,
    address: str = "localhost:11434",
) -> str:
    """ローカルLLM（OllamaやLM Studio）にリクエストを送信する関数

    OpenAI互換APIを使用して、指定されたアドレスのローカルLLMにリクエストを送信します。

    Args:
        messages: チャットメッセージのリスト
        model: 使用するモデル名
        is_json: JSONレスポンスを要求するかどうか
        json_schema: JSONスキーマ（Pydanticモデルまたは辞書）
        address: ローカルLLMのアドレス（例: 127.0.0.1:1234）

    Returns:
        LLMからのレスポンス
    """
    try:
        if ":" in address:
            host, port_str = address.split(":")
            port = int(port_str)
        else:
            host = address
            port = 11434  # デフォルトポート
    except ValueError:
        logging.warning(f"Invalid address format: {address}, using default")
        host = "localhost"
        port = 11434

    base_url = f"http://{host}:{port}/v1"

    try:
        client = OpenAI(
            base_url=base_url,
            api_key="not-needed",  # OllamaとLM Studioは認証不要
        )

        response_format = None
        if is_json:
            response_format = {"type": "json_object"}
        if json_schema and isinstance(json_schema, dict):
            response_format = json_schema
        if json_schema and isinstance(json_schema, type) and issubclass(json_schema, BaseModel):
            response_format = {
                "type": "json_schema",
                "json_schema": {
                    "name": json_schema.__name__,
                    "strict": True,  # ← スキーマ逸脱を弾く
                    "schema": json_schema.schema(),
                },
            }

        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0,
            "n": 1,
            "seed": 0,
            "timeout": 30,
        }

        if response_format:
            payload["response_format"] = response_format

        response = client.chat.completions.create(**payload)

        return response.choices[0].message.content
    except Exception as e:
        logging.error(
            f"[LocalLLM][APIError] model={model}, address={address}, error={e}, messages={messages}, response_format={response_format}"
        )
        raise


def request_to_openrouter(
    messages: list[dict],
    model: str,
    is_json: bool = False,
    json_schema: dict | type[BaseModel] | None = None,
) -> str:
    """OpenRouterにリクエストを送信する関数

    Args:
        messages: チャットメッセージのリスト
        model: 使用するモデル名
        is_json: JSONレスポンスを要求するかどうか
        json_schema: JSONスキーマ（Pydanticモデルまたは辞書）

    Returns:
        LLMからのレスポンス
    """
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY environment variable is not set")

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        default_headers={
            "HTTP-Referer": os.getenv("NEXT_PUBLIC_SITE_URL", "http://localhost:3000"),
            "X-Title": "Kouchou AI",
        },
    )

    try:
        response_format = None
        if is_json:
            response_format = {"type": "json_object"}
        if json_schema:
            # BaseModelの場合はdict化して渡す
            if isinstance(json_schema, type) and issubclass(json_schema, BaseModel):
                response_format = {
                    "type": "json_schema",
                    "json_schema": {
                        "name": json_schema.__name__,
                        "strict": True,
                        "schema": json_schema.schema(),
                    },
                }
            else:
                response_format = json_schema

        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0,
            "n": 1,
            "seed": 0,
            "timeout": 30,
        }
        if response_format:
            payload["response_format"] = response_format

        response = client.chat.completions.create(**payload)
        if not response or not hasattr(response, "choices") or not response.choices:
            logging.error(f"[OpenRouter][ResponseError] model={model}, response={response}, payload={payload}")
            raise RuntimeError("OpenRouter API returned no choices or invalid response.")
        return response.choices[0].message.content
    except openai.RateLimitError as e:
        logging.warning(f"[OpenRouter][RateLimit] model={model}, error={e}, messages={messages}")
        raise
    except openai.AuthenticationError as e:
        logging.error(f"[OpenRouter][AuthError] model={model}, error={str(e)}, messages={messages}")
        raise
    except openai.BadRequestError as e:
        logging.error(f"[OpenRouter][BadRequest] model={model}, error={str(e)}, messages={messages}")
        raise


class ProviderService:
    """LLMプロバイダーごとのAPI呼び出しを一元管理するサービスクラス"""

    def chat(
        self,
        messages: list[dict],
        model: str = "gpt-4o",
        is_json: bool = False,
        json_schema: dict | type[BaseModel] | None = None,
        provider: str = "openai",
        local_llm_address: str | None = None,
    ) -> str:
        if provider == "azure":
            return request_to_azure_chatcompletion(messages, is_json, json_schema)
        elif provider == "openai":
            return request_to_openai(messages, model, is_json, json_schema)
        elif provider == "openrouter":
            return request_to_openrouter(messages, model, is_json, json_schema)
        elif provider == "local":
            address = local_llm_address or "localhost:11434"
            return request_to_local_llm(messages, model, is_json, json_schema, address)
        else:
            raise ValueError(f"Unknown provider: {provider}")


EMBDDING_MODELS = [
    "text-embedding-3-large",
    "text-embedding-3-small",
]


def _validate_model(model):
    if model not in EMBDDING_MODELS:
        raise RuntimeError(f"Invalid embedding model: {model}, available models: {EMBDDING_MODELS}")


def request_to_local_llm_embed(args, model, address="localhost:11434"):
    """ローカルLLM（OllamaやLM Studio）を使用して埋め込みを取得する関数

    OpenAI互換APIを使用して、指定されたアドレスのローカルLLMから埋め込みを取得します。

    Args:
        args: 埋め込みを取得するテキスト
        model: 使用するモデル名
        address: ローカルLLMのアドレス（例: 127.0.0.1:1234）

    Returns:
        埋め込みベクトルのリスト
    """
    try:
        if ":" in address:
            host, port_str = address.split(":")
            port = int(port_str)
        else:
            host = address
            port = 11434  # デフォルトポート
    except ValueError:
        logging.warning(f"Invalid address format: {address}, using default")
        host = "localhost"
        port = 11434

    base_url = f"http://{host}:{port}/v1"

    try:
        client = OpenAI(
            base_url=base_url,
            api_key="not-needed",  # OllamaとLM Studioは認証不要
        )

        response = client.embeddings.create(input=args, model=model)
        embeds = [item.embedding for item in response.data]
        return embeds
    except Exception as e:
        logging.error(f"LocalLLM embedding API error: {e}")
        logging.warning("Falling back to local embedding")
        return request_to_local_embed(args)


def request_to_openrouter_embed(args, model):
    """OpenRouterを使用して埋め込みを取得する関数

    Args:
        args: 埋め込みを取得するテキスト
        model: 使用するモデル名

    Returns:
        埋め込みベクトルのリスト
    """
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY environment variable is not set")

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        default_headers={
            "HTTP-Referer": os.getenv("NEXT_PUBLIC_SITE_URL", "http://localhost:3000"),
            "X-Title": "Kouchou AI",
        },
    )

    try:
        response = client.embeddings.create(input=args, model=model)
        embeds = [item.embedding for item in response.data]
        return embeds
    except openai.RateLimitError as e:
        logging.warning(f"OpenRouter API rate limit hit: {e}")
        raise
    except openai.AuthenticationError as e:
        logging.error(f"OpenRouter API authentication error: {str(e)}")
        raise
    except openai.BadRequestError as e:
        logging.error(f"OpenRouter API bad request error: {str(e)}")
        raise


def request_to_embed(
    args, model, is_embedded_at_local=False, provider: str | None = None, local_llm_address: str | None = None
):
    if is_embedded_at_local:
        return request_to_local_embed(args)

    if provider == "azure":
        return request_to_azure_embed(args, model)
    elif provider == "openai":
        _validate_model(model)
        client = OpenAI()
        response = client.embeddings.create(input=args, model=model)
        embeds = [item.embedding for item in response.data]
        return embeds
    elif provider == "openrouter":
        return request_to_openrouter_embed(args, model)
    elif provider == "local":
        address = local_llm_address or "localhost:11434"
        return request_to_local_llm_embed(args, model, address)
    else:
        raise ValueError(f"Unknown provider: {provider}")


def request_to_azure_embed(args, model):
    azure_endpoint = os.getenv("AZURE_EMBEDDING_ENDPOINT")
    api_key = os.getenv("AZURE_EMBEDDING_API_KEY")
    api_version = os.getenv("AZURE_EMBEDDING_VERSION")
    deployment = os.getenv("AZURE_EMBEDDING_DEPLOYMENT_NAME")

    client = AzureOpenAI(
        api_version=api_version,
        azure_endpoint=azure_endpoint,
        api_key=api_key,
    )

    response = client.embeddings.create(input=args, model=deployment)
    return [item.embedding for item in response.data]


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
    # print(request_to_embed("Hello", "text-embedding-3-large"))
    print(request_to_azure_embed("Hello", "text-embedding-3-large"))


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


def _local_llm_test():
    # ローカルLLMにリクエストを送信するテスト
    messages = [
        {"role": "system", "content": "Translate the following text to English."},
        {"role": "user", "content": "これはテストです"},
    ]
    response = request_to_local_llm(messages=messages, model="llama-3-elyza-jp-8b", address="localhost:1234")
    print("Local LLM response example:")
    print(response)


# OpenRouterで許可するモデルIDリスト
OPENROUTER_ALLOWED_MODELS = [
    "openai/gpt-4o",
    "openai/gpt-4o-mini",
    "openai/gpt-4-1106-preview",
    "google/gemini-2.5-pro-preview",
]


def get_available_models(provider: str, address: str | None = None) -> dict[str, list[dict[str, str]]]:
    """
    指定されたプロバイダーで利用可能なモデルのリストを取得する関数。
    返却値は必ず {"available": [...], "supported": [...]} の辞書。
    available: 実際に利用可能なモデルリスト
    supported: サポート対象モデルリスト（通常はavailableと同じ）
    """
    if provider not in LLM_PROVIDERS:
        raise ValueError(f"Unknown provider: {provider}")

    if provider == "openai":
        return {
            "available": [
                {"value": "gpt-4o-mini", "label": "GPT-4o mini"},
                {"value": "gpt-4o", "label": "GPT-4o"},
                {"value": "o3-mini", "label": "o3-mini"},
            ],
            "supported": [
                {"value": "gpt-4o-mini", "label": "GPT-4o mini"},
                {"value": "gpt-4o", "label": "GPT-4o"},
                {"value": "o3-mini", "label": "o3-mini"},
            ]
        }
    elif provider == "azure":
        return {
            "available": [
                {"value": "gpt-4o-mini", "label": "GPT-4o mini"},
                {"value": "gpt-4o", "label": "GPT-4o"},
                {"value": "o3-mini", "label": "o3-mini"},
            ],
            "supported": [
                {"value": "gpt-4o-mini", "label": "GPT-4o mini"},
                {"value": "gpt-4o", "label": "GPT-4o"},
                {"value": "o3-mini", "label": "o3-mini"},
            ]
        }
    elif provider == "openrouter":
        try:
            api_key = os.getenv("OPENROUTER_API_KEY")
            if not api_key:
                raise ValueError("OPENROUTER_API_KEY environment variable is not set")

            client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=api_key,
                default_headers={
                    "HTTP-Referer": os.getenv("NEXT_PUBLIC_SITE_URL", "http://localhost:3000"),
                    "X-Title": "Kouchou AI",
                },
            )

            response = client.models.list()
            return {
                "available": [
                    {
                        "value": model.id,
                        "label": (
                            model.id
                            if not getattr(model, "name", None) or str(model.name).lower() == "unknown"
                            else f"{model.name} ({model.id})"
                        ),
                    }
                    for model in response.data
                    if model.id in OPENROUTER_ALLOWED_MODELS
                ],
                "supported": [
                    {
                        "value": model.id,
                        "label": (
                            model.id
                            if not getattr(model, "name", None) or str(model.name).lower() == "unknown"
                            else f"{model.name} ({model.id})"
                        ),
                    }
                    for model in response.data
                ]
            }
        except Exception as e:
            logging.error(f"Failed to fetch OpenRouter models: {e}")
            return {"available": [], "supported": []}
    elif provider == "local":
        try:
            if not address:
                address = "localhost:11434"

            if ":" in address:
                host, port_str = address.split(":")
                port = int(port_str)
            else:
                host = address
                port = 11434

            base_url = f"http://{host}:{port}/v1"

            client = OpenAI(
                base_url=base_url,
                api_key="not-needed",  # OllamaとLM Studioは認証不要
            )

            response = client.models.list()
            return {
                "available": [
                    {
                        "value": model.id,
                        "label": (
                            f"{model.name} ({model.id})"
                            if getattr(model, "name", None) and str(model.name).lower() != "unknown"
                            else model.id
                        ),
                    }
                    for model in response.data
                ],
                "supported": [
                    {
                        "value": model.id,
                        "label": (
                            f"{model.name} ({model.id})"
                            if getattr(model, "name", None) and str(model.name).lower() != "unknown"
                            else model.id
                        ),
                    }
                    for model in response.data
                ]
            }
        except Exception as e:
            logging.error(f"Failed to fetch LocalLLM models: {e}")
            return {"available": [], "supported": []}
    else:
        raise ValueError(f"Unknown provider: {provider}")


def request_to_chat_openai(
    messages: list[dict],
    model: str = "gpt-4o",
    is_json: bool = False,
    json_schema: dict | type[BaseModel] | None = None,
    provider: str = "openai",
    local_llm_address: str | None = None,
) -> str:
    """
    指定されたLLMプロバイダーに対してチャットリクエストを送信する。
    ProviderServiceクラスのラッパー。
    """
    return ProviderService().chat(
        messages=messages,
        model=model,
        is_json=is_json,
        json_schema=json_schema,
        provider=provider,
        local_llm_address=local_llm_address,
    )


if __name__ == "__main__":
    # _test()
    # _test()
    # _jsonschema_test()
    # _basemodel_test()
    # _local_emb_test()
    # _local_llm_test()
    pass
