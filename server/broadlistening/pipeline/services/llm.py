import logging
import os
import threading
import time
import random

import openai
from dotenv import load_dotenv
from openai import AzureOpenAI, OpenAI
from pydantic import BaseModel
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

try:  # Optional dependency
    import google.generativeai as genai
    from google.api_core import exceptions as google_exceptions
except ModuleNotFoundError:  # pragma: no cover - library might be unavailable in tests
    genai = None
    google_exceptions = None

DOTENV_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../../.env"))
load_dotenv(DOTENV_PATH)


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
    user_api_key: str | None = None,
) -> tuple[str, int, int, int]:  # 戻り値を文字列とトークン使用量(入力・出力・合計)のタプルに変更
    openai.api_type = "openai"
    token_usage_input = 0  # 入力トークン使用量を追跡する変数
    token_usage_output = 0  # 出力トークン使用量を追跡する変数
    token_usage_total = 0  # 合計トークン使用量を追跡する変数

    client = OpenAI(api_key=user_api_key) if user_api_key else OpenAI()

    try:
        if isinstance(json_schema, type) and issubclass(json_schema, BaseModel):
            # Use beta.chat.completions.create for Pydantic BaseModel
            response = client.beta.chat.completions.parse(
                model=model,
                messages=messages,
                temperature=0,
                n=1,
                seed=0,
                response_format=json_schema,
                timeout=30,
            )
            if hasattr(response, "usage") and response.usage:
                token_usage_input = response.usage.prompt_tokens or 0
                token_usage_output = response.usage.completion_tokens or 0
                token_usage_total = response.usage.total_tokens or 0
            return response.choices[0].message.content, token_usage_input, token_usage_output, token_usage_total

        else:
            response_format = None
            if is_json:
                response_format = {"type": "json_object"}
            if json_schema:  # 両方有効化されていたら、json_schemaを優先
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

            if hasattr(response, "usage") and response.usage:
                token_usage_input = response.usage.prompt_tokens or 0
                token_usage_output = response.usage.completion_tokens or 0
                token_usage_total = response.usage.total_tokens or 0

            return response.choices[0].message.content, token_usage_input, token_usage_output, token_usage_total
    except openai.RateLimitError as e:
        logging.warning(f"OpenAI API rate limit hit: {e}")
        raise
    except openai.AuthenticationError as e:
        logging.error(f"OpenAI API authentication error: {str(e)}")
        raise
    except openai.BadRequestError as e:
        logging.error(f"OpenAI API bad request error: {str(e)}")
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
    user_api_key: str | None = None,
) -> tuple[str, int, int, int]:  # 戻り値を文字列とトークン使用量(入力・出力・合計)のタプルに変更
    azure_endpoint = os.getenv("AZURE_CHATCOMPLETION_ENDPOINT")
    deployment = os.getenv("AZURE_CHATCOMPLETION_DEPLOYMENT_NAME")
    api_key = user_api_key or os.getenv("AZURE_CHATCOMPLETION_API_KEY")
    api_version = os.getenv("AZURE_CHATCOMPLETION_VERSION")
    token_usage_input = 0  # 入力トークン使用量を追跡する変数
    token_usage_output = 0  # 出力トークン使用量を追跡する変数
    token_usage_total = 0  # 合計トークン使用量を追跡する変数

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
            if hasattr(response, "usage") and response.usage:
                token_usage_input = response.usage.prompt_tokens or 0
                token_usage_output = response.usage.completion_tokens or 0
                token_usage_total = response.usage.total_tokens or 0
            return (
                response.choices[0].message.parsed.model_dump(),
                token_usage_input,
                token_usage_output,
                token_usage_total,
            )
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

            if hasattr(response, "usage") and response.usage:
                token_usage_input = response.usage.prompt_tokens or 0
                token_usage_output = response.usage.completion_tokens or 0
                token_usage_total = response.usage.total_tokens or 0

            return response.choices[0].message.content, token_usage_input, token_usage_output, token_usage_total
    except openai.RateLimitError as e:
        logging.warning(f"OpenAI API rate limit hit: {e}")
        raise
    except openai.AuthenticationError as e:
        logging.error(f"OpenAI API authentication error: {str(e)}")
        raise
    except openai.BadRequestError as e:
        logging.error(f"OpenAI API bad request error: {str(e)}")
        raise


def request_to_gemini_chatcompletion(
    messages: list[dict],
    model: str = "gemini-2.5-flash",
    is_json: bool = False,
    json_schema: dict | type[BaseModel] | None = None,
    user_api_key: str | None = None,
) -> tuple[str, int, int, int]:
    token_usage_input = 0
    token_usage_output = 0
    token_usage_total = 0

    if genai is None or google_exceptions is None:  # pragma: no cover - optional dependency
        raise RuntimeError("google-generativeai is required for Gemini provider")

    api_key = user_api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY")
    genai.configure(api_key=api_key)

    system_instruction = "\n".join(
        m["content"] for m in messages if m.get("role") == "system"
    ) or None

    history = [
        {
            "role": "user" if m.get("role") == "user" else "model",
            "parts": [m.get("content", "")],
        }
        for m in messages
        if m.get("role") != "system"
    ]

    model_client = genai.GenerativeModel(
        model, system_instruction=system_instruction
    )

    def _remove_title_keys(obj: dict | list) -> dict | list:
        """Recursively remove `title` keys from JSON schema objects."""

        if isinstance(obj, dict):
            obj.pop("title", None)
            for value in obj.values():
                _remove_title_keys(value)
        elif isinstance(obj, list):
            for item in obj:
                _remove_title_keys(item)
        return obj
    
    def _normalize_openai_response_format(schema: dict | None) -> tuple[dict | None, bool]:
        """
        OpenAIのresponse_formatをGemini用へ正規化する。
        戻り値: (raw_schema or None, json_mode_only_flag)
        - json_mode_only_flag=True のときは response_mime_typeのみを設定（スキーマ無しJSONモード）
        """
        if not isinstance(schema, dict):
            return None, False

        # OpenAI: {"type":"json_object"} → スキーマ無しの JSON モード
        if schema.get("type") == "json_object":
            return None, True

        # OpenAI: {"type": "json_schema", "json_schema": {...}} → 中の素スキーマを取り出す
        if schema.get("type") == "json_schema" and "json_schema" in schema:
            inner = schema["json_schema"]
            # OpenRouter等で {"json_schema": {"schema": {...}, "name": "...", "strict": ...}} の場合もあり得る
            if isinstance(inner, dict) and "schema" in inner:
                inner = inner["schema"]
            # 余計なメタ（name/strictなど）は落とす
            if isinstance(inner, dict):
                inner.pop("name", None)
                inner.pop("strict", None)
            return inner, False

        # 既に“素のスキーマ”が来ているケースはそのまま（後で title 削除）
        return schema, False

    generation_config = None
    # Pydantic → 素のJSONスキーマ化
    if isinstance(json_schema, type) and issubclass(json_schema, BaseModel):
        schema = json_schema.model_json_schema()
        schema = _remove_title_keys(schema)
        generation_config = genai.GenerationConfig(
            response_mime_type="application/json",
            response_schema=schema,
        )

    # dict → OpenAIラッパーを剥がしてからセット
    elif isinstance(json_schema, dict):
        raw_schema, json_only = _normalize_openai_response_format(json_schema)
        if json_only:
            generation_config = genai.GenerationConfig(
                response_mime_type="application/json"
            )
        else:
            schema = _remove_title_keys(raw_schema) if raw_schema else None
            generation_config = genai.GenerationConfig(
                response_mime_type="application/json",
                **({"response_schema": schema} if schema else {}),
            )

    elif is_json:
        generation_config = genai.GenerationConfig(
            response_mime_type="application/json"
        )

    max_retries = 5
    base_wait = 8

    for attempt in range(max_retries):
        try:
            response = model_client.generate_content(
                history, generation_config=generation_config
            )
            usage = getattr(response, "usage_metadata", None)
            if usage:
                token_usage_input = getattr(usage, "prompt_token_count", 0) or 0
                token_usage_output = getattr(usage, "candidates_token_count", 0) or 0
                token_usage_total = getattr(usage, "total_token_count", 0) or 0
            
            try:
                # candidates, prompt_feedback 等を安全にログ化
                cands = getattr(response, "candidates", None)
                finish_reasons = []
                safety = []
                if cands:
                    for i, c in enumerate(cands):
                        fr = getattr(c, "finish_reason", None)
                        finish_reasons.append(fr)
                        sr = getattr(c, "safety_ratings", None)
                        if sr:
                            safety.append([getattr(r, "category", None) for r in sr])
                    logging.debug("[Gemini] Candidates=%d, finish_reasons=%s, safety_categories=%s",
                                  len(cands), finish_reasons, safety)

                pf = getattr(response, "prompt_feedback", None)
                if pf:
                    try:
                        pf_dict = pf.to_dict() if hasattr(pf, "to_dict") else pf.__dict__
                    except Exception:
                        pf_dict = str(pf)
                    logging.debug("[Gemini] Prompt feedback=%s", pf_dict)
            except Exception as log_ex:
                logging.debug("[Gemini] Response meta logging failed: %s", log_ex)
            
            text = response.text
            if isinstance(json_schema, type) and issubclass(json_schema, BaseModel):
                try:
                    parsed = json_schema.model_validate_json(text).model_dump()
                except Exception:  # pragma: no cover - validation error
                    parsed = text
                return (
                    parsed,
                    token_usage_input,
                    token_usage_output,
                    token_usage_total,
                )
            return text, token_usage_input, token_usage_output, token_usage_total
        except google_exceptions.Unauthenticated as e:
            logging.error(f"Gemini API authentication error: {e}")
            raise
        except google_exceptions.InvalidArgument as e:
            logging.error(f"Gemini API bad request error: {e}")
            raise
        except google_exceptions.GoogleAPICallError as e:
            status_code = getattr(e, "code", None)
            is_rate_limit = (status_code == 429) or isinstance(e, google_exceptions.ResourceExhausted)

            if not is_rate_limit:
                logging.error(f"Gemini API error: {e}")
                raise

            last_exc = e
            retry_delay: int | str | None = getattr(e, "retry_delay", None)
            response_data = getattr(e, "response", None)
            if retry_delay is None and isinstance(response_data, dict):
                retry_delay = (
                    response_data.get("error", {})
                    .get("details", [{}])[0]
                    .get("metadata", {})
                    .get("retry_delay")
                )

            wait_time: int
            if isinstance(retry_delay, str) and retry_delay.endswith("s"):
                retry_delay = retry_delay[:-1]
            try:
                wait_time = int(retry_delay) if retry_delay is not None else 0
            except (TypeError, ValueError):
                wait_time = 0

            if wait_time <= 0:
                wait_time = int((base_wait * (2 ** attempt)) * (0.5 + random.random()))
                wait_time = min(wait_time, 60)

            last_wait = wait_time

            if attempt >= max_retries - 1:
                logging.error(
                    "Gemini API rate limit exceeded repeatedly. Free tier allows 15 requests per minute per model. Consider upgrading to a paid plan."
                )
                raise

            time.sleep(wait_time)

    raise RuntimeError("Gemini API call failed after retries")

def request_to_local_llm(
    messages: list[dict],
    model: str,
    is_json: bool = False,
    json_schema: dict | type[BaseModel] | None = None,
    address: str = "localhost:11434",
) -> tuple[str, int, int, int]:  # 戻り値を文字列とトークン使用量(入力・出力・合計)のタプルに変更
    """ローカルLLM（OllamaやLM Studio）にリクエストを送信する関数

    OpenAI互換APIを使用して、指定されたアドレスのローカルLLMにリクエストを送信します。

    Args:
        messages: チャットメッセージのリスト
        model: 使用するモデル名
        is_json: JSONレスポンスを要求するかどうか
        json_schema: JSONスキーマ（Pydanticモデルまたは辞書）
        address: ローカルLLMのアドレス（例: 127.0.0.1:1234）

    Returns:
        LLMからのレスポンスとトークン使用量(入力・出力・合計)のタプル
    """
    token_usage_input = 0  # 入力トークン使用量を追跡する変数
    token_usage_output = 0  # 出力トークン使用量を追跡する変数
    token_usage_total = 0  # 合計トークン使用量を追跡する変数
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

        if hasattr(response, "usage") and response.usage:
            token_usage_input = response.usage.prompt_tokens or 0
            token_usage_output = response.usage.completion_tokens or 0
            token_usage_total = response.usage.total_tokens or 0

        return response.choices[0].message.content, token_usage_input, token_usage_output, token_usage_total
    except Exception as e:
        logging.error(
            f"LocalLLM API error: {e}, model:{model}, address:{address}, is_json:{is_json}, json_schema:{json_schema}, response_format:{response_format}"
        )
        raise


def request_to_chat_ai(
    messages: list[dict],
    model: str = "gpt-4o",
    is_json: bool = False,
    json_schema: dict | type[BaseModel] | None = None,
    provider: str = "openai",
    local_llm_address: str | None = None,
    user_api_key: str | None = None,
) -> tuple[str, int, int, int]:  # 戻り値を文字列とトークン使用量(入力・出力・合計)のタプルに変更
    """AIプロバイダーにチャットリクエストを送信する関数

    Args:
        messages: チャットメッセージのリスト
        model: 使用するモデル名
        is_json: JSONレスポンスを要求するかどうか
        json_schema: JSONスキーマ（Pydanticモデルまたは辞書）
        provider: 使用するプロバイダー（"openai", "azure", "local", "openrouter", "gemini"）
        local_llm_address: ローカルLLMのアドレス（provider="local"の場合のみ使用）

    Returns:
        AIからのレスポンスとトークン使用量(入力・出力・合計)のタプル

    Note:
        - provider="openai": OpenAI APIを使用
        - provider="azure": Azure OpenAI APIを使用
        - provider="local": ローカルLLM（OllamaやLM Studio）を使用
        - provider="gemini": Google Gemini APIを使用
        - provider="openrouter": OpenRouter APIを使用（OpenAIやGeminiのモデルにアクセス可能）
        - provider="gemini": Google Gemini APIを使用
    """
    if provider == "azure":
        return request_to_azure_chatcompletion(messages, is_json, json_schema, user_api_key)
    elif provider == "openai":
        return request_to_openai(messages, model, is_json, json_schema, user_api_key)
    elif provider == "local":
        address = local_llm_address or "localhost:11434"
        return request_to_local_llm(messages, model, is_json, json_schema, address)
    elif provider == "gemini":
        return request_to_gemini_chatcompletion(messages, model, is_json, json_schema, user_api_key)
    elif provider == "openrouter":
        # OpenRouterのモデル名を直接使用
        return request_to_openrouter_chatcompletion(messages, model, is_json, json_schema, user_api_key)
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


def request_to_embed(
    args,
    model,
    is_embedded_at_local=False,
    provider="openai",
    local_llm_address: str | None = None,
    user_api_key: str | None = None,
):
    if is_embedded_at_local:
        return request_to_local_embed(args)

    if provider == "azure":
        logging.info("request_to_azure_embed")
        return request_to_azure_embed(args, model, user_api_key)
    elif provider == "openai":
        logging.info("request_to_openai_embed")
        _validate_model(model)
        client = OpenAI(api_key=user_api_key) if user_api_key else OpenAI()
        response = client.embeddings.create(input=args, model=model)
        embeds = [item.embedding for item in response.data]
        return embeds
    elif provider == "gemini":
        logging.info("request_to_gemini_embed")
        # OpenAI名や未指定が来たら Gemini 既定に置き換える
        openai_aliases = {"text-embedding-3-large", "text-embedding-3-small"}
        resolved_model = model
        if not resolved_model or resolved_model in openai_aliases:
            resolved_model = "gemini-embedding-001"
        return request_to_gemini_embed(args, resolved_model, user_api_key)
    elif provider == "openrouter":
        raise NotImplementedError("OpenRouter embedding support is not implemented yet")
    elif provider == "local":
        address = local_llm_address or "localhost:11434"
        return request_to_local_llm_embed(args, model, address)
    else:
        raise ValueError(f"Unknown provider: {provider}")


def request_to_gemini_embed(args, model, user_api_key: str | None = None):
    if genai is None:
        raise RuntimeError("google-generativeai is required for Gemini provider")

    api_key = user_api_key or os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY environment variable is not set")

    genai.configure(api_key=api_key)

    if isinstance(args, str):
        args = [args]

    embeds: list[list[float]] = []
    for text in args:
        response = genai.embed_content(model=model, content=text)
        embedding = (
            response["embedding"]
            if isinstance(response, dict)
            else getattr(response, "embedding", None)
        )
        embeds.append(embedding)

    return embeds


def request_to_azure_embed(args, model, user_api_key: str | None = None):
    azure_endpoint = os.getenv("AZURE_EMBEDDING_ENDPOINT")
    api_key = user_api_key or os.getenv("AZURE_EMBEDDING_API_KEY")
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

    response = request_to_chat_ai(messages=messages, model="gpt-4o", json_schema=response_format)
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

    response = request_to_chat_ai(messages=messages, model="gpt-4o", json_schema=CalendarEvent)

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

@retry(
    retry=retry_if_exception_type(openai.RateLimitError),
    wait=wait_exponential(multiplier=3, min=3, max=20),
    stop=stop_after_attempt(3),
    reraise=True,
)
def request_to_openrouter_chatcompletion(
    messages: list[dict],
    model: str,
    is_json: bool = False,
    json_schema: dict | type[BaseModel] = None,
    user_api_key: str | None = None,
) -> tuple[str, int, int, int]:  # 戻り値を文字列とトークン使用量(入力・出力・合計)のタプルに変更
    api_key = user_api_key or os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY environment variable is not set")

    token_usage_input = 0  # 入力トークン使用量を追跡する変数
    token_usage_output = 0  # 出力トークン使用量を追跡する変数
    token_usage_total = 0  # 合計トークン使用量を追跡する変数

    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
    )

    try:
        if isinstance(json_schema, type) and issubclass(json_schema, BaseModel):
            response = client.beta.chat.completions.parse(
                model=model,
                messages=messages,
                temperature=0,
                n=1,
                seed=0,
                response_format=json_schema,
                timeout=30,
            )
            if hasattr(response, "usage") and response.usage:
                token_usage_input = response.usage.prompt_tokens or 0
                token_usage_output = response.usage.completion_tokens or 0
                token_usage_total = response.usage.total_tokens or 0
            return response.choices[0].message.content, token_usage_input, token_usage_output, token_usage_total
        else:
            payload = {
                "model": model,
                "messages": messages,
                "temperature": 0,
                "n": 1,
                "seed": 0,
                "timeout": 30,
            }

            if is_json:
                payload["response_format"] = {"type": "json_object"}
            if json_schema:  # 両方有効化されていたら、json_schemaを優先
                payload["response_format"] = json_schema

            response = client.chat.completions.create(**payload)
            if hasattr(response, "usage") and response.usage:
                token_usage_input = response.usage.prompt_tokens or 0
                token_usage_output = response.usage.completion_tokens or 0
                token_usage_total = response.usage.total_tokens or 0
            return response.choices[0].message.content, token_usage_input, token_usage_output, token_usage_total
    except openai.RateLimitError as e:
        logging.warning(f"OpenRouter API rate limit hit: {e}")
        raise
    except openai.AuthenticationError as e:
        logging.error(f"OpenRouter API authentication error: {str(e)}")
        raise
    except openai.BadRequestError as e:
        logging.error(f"OpenRouter API bad request error: {str(e)}")
        raise


if __name__ == "__main__":
    # _test()
    # _test()
    # _jsonschema_test()
    # _basemodel_test()
    # _local_emb_test()
    # _local_llm_test()
    pass
