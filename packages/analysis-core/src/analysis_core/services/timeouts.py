"""LLM request timeout configuration shared by API and CLI execution."""

import os

from dotenv import load_dotenv

load_dotenv()


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


def resolve_timeout(value: object = None) -> int:
    return DEFAULT_REQUEST_TIMEOUT_SECONDS if value is None else positive_timeout(value)
