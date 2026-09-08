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


DEFAULT_REQUEST_TIMEOUT_SECONDS = positive_timeout(os.getenv("LLM_REQUEST_TIMEOUT_SECONDS", "300"))


def resolve_timeout(value: object = None) -> int:
    return DEFAULT_REQUEST_TIMEOUT_SECONDS if value is None else positive_timeout(value)
