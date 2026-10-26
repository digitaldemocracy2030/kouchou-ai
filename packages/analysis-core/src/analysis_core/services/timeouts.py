"""LLM request timeout configuration shared by API and CLI execution."""

import os

from analysis_core.env_file import load_env_file

load_env_file()


def positive_timeout(value: object) -> int:
    """Accept positive integer seconds, without silently truncating fractions."""
    if isinstance(value, bool) or not isinstance(value, (str, int)):
        raise ValueError("LLM timeout must be a positive integer number of seconds")
    try:
        seconds = int(value)
    except ValueError as exc:
        raise ValueError("LLM timeout must be a positive integer number of seconds") from exc
    if seconds <= 0:
        raise ValueError("LLM timeout must be a positive integer number of seconds")
    return seconds


def _request_timeout_from_env() -> int:
    # 空欄は未設定として扱う (OPENAI_FLEX_TIMEOUT_SECONDS と同じ)
    raw = (os.getenv("LLM_REQUEST_TIMEOUT_SECONDS") or "").strip() or "300"
    try:
        return positive_timeout(raw)
    except ValueError as exc:
        raise ValueError(
            f"LLM_REQUEST_TIMEOUT_SECONDS must be a positive integer number of seconds (got {raw!r})"
        ) from exc


DEFAULT_REQUEST_TIMEOUT_SECONDS = _request_timeout_from_env()


# Flex はレイテンシが大きいため、OpenAI は 15 分程度のタイムアウトを推奨している。
DEFAULT_OPENAI_FLEX_TIMEOUT_SECONDS = 900


def openai_flex_timeout_from_env() -> int:
    """OPENAI_FLEX_TIMEOUT_SECONDS を読む。不正な値は変数名を示す ValueError にする。

    リクエストのたびに検証すると、エラーが抽出などの失敗（型名だけの記録）に埋もれるので、
    起動時の validate_api_keys からも呼んで即座に止める。
    """
    # 空文字は未設定として扱う (.env.example の空欄をそのまま使えるように)
    raw = (os.getenv("OPENAI_FLEX_TIMEOUT_SECONDS") or "").strip() or str(DEFAULT_OPENAI_FLEX_TIMEOUT_SECONDS)
    try:
        return positive_timeout(raw)
    except ValueError as exc:
        raise ValueError(
            f"OPENAI_FLEX_TIMEOUT_SECONDS must be a positive integer number of seconds (got {raw!r})"
        ) from exc


def resolve_timeout(value: object = None) -> int:
    return DEFAULT_REQUEST_TIMEOUT_SECONDS if value is None else positive_timeout(value)
