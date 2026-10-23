"""失敗の理由をログに残すための、例外の要約と秘密情報の伏せ字。

抽出・ラベル生成・意見分類は失敗を例外の型名で分類して status / 診断に残すが、型名だけでは
設定誤りなどの原因が分からない。そこで通常ログには例外のメッセージも出す。ただし SDK の
例外メッセージには API キー（の一部）が入ることがあるので、必ずここで伏せ字にしてから出す。
"""

import os
import re
from collections.abc import Iterable

from pydantic import ValidationError

REDACTED = "[REDACTED]"
MAX_MESSAGE_CHARS = 300

# 名前がこれらで終わる環境変数の値は秘密情報として扱う（OPENAI_API_KEY, USER_API_KEY など）
_SECRET_ENV_SUFFIXES = ("_KEY", "_SECRET", "_TOKEN", "_PASSWORD")
# 短すぎる値を伏せると無関係な語まで消えるため、一定以上の長さの値だけを対象にする
_MIN_SECRET_LENGTH = 6

_SECRET_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    # OpenAI / OpenRouter のキー（OpenAI が一部を * で伏せて返す形も含む）
    (re.compile(r"\bsk-[A-Za-z0-9_\-\*]{6,}"), REDACTED),
    # Google (Gemini) の API キー
    (re.compile(r"\bAIza[0-9A-Za-z_\-]{10,}"), REDACTED),
    # Authorization: Bearer <token>
    (re.compile(r"(?i)\bbearer\s+[^\s'\",]+"), f"Bearer {REDACTED}"),
    # key=..., api_key: ..., token=... などの値（URL のクエリを含む）
    (
        re.compile(
            r"(?i)(?<![A-Za-z])((?:api[_-]?key|key|token|secret|password|access[_-]?token)[\"']?\s*[:=]\s*[\"']?)"
            r"[^\s'\",&}]+"
        ),
        rf"\1{REDACTED}",
    ),
    # 上に当てはまらない長いトークン（Azure のキーは 32 桁の 16 進など）
    (re.compile(r"(?<![A-Za-z0-9_\-])[A-Za-z0-9_\-]{32,}(?![A-Za-z0-9_\-])"), REDACTED),
)


def _configured_secrets() -> list[str]:
    return [
        value
        for name, value in os.environ.items()
        if name.upper().endswith(_SECRET_ENV_SUFFIXES) and value and len(value.strip()) >= _MIN_SECRET_LENGTH
    ]


def redact_secrets(text: str, secrets: Iterable[str | None] = ()) -> str:
    """API キーなどの秘密情報らしい部分を伏せ字にする。

    環境変数に設定されたキーの値・呼び出し元が渡した値（config の user_api_key など）は
    完全一致で、それ以外はキーの形のパターンで伏せる。
    """
    known = [s.strip() for s in (*secrets, *_configured_secrets()) if s and len(s.strip()) >= _MIN_SECRET_LENGTH]
    # 長い値から置き換え、短い値が長い値の一部だけを置き換えて残りが見えるのを防ぐ
    for secret in sorted(set(known), key=len, reverse=True):
        text = text.replace(secret, REDACTED)
    for pattern, replacement in _SECRET_PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def summarize_exception(exc: BaseException, secrets: Iterable[str | None] = ()) -> str:
    """ログ用に「型名: 伏せ字済みの 1 行メッセージ」を返す。

    伏せ字は切り詰めの前に行う（途中で切れたキーはパターンに一致しなくなるため）。
    """
    name = type(exc).__name__
    if isinstance(exc, ValidationError):
        # pydantic の既定のメッセージは input_value に LLM の応答本文（意見の文面を含みうる）を
        # 載せるので、項目と理由だけにする
        message = "; ".join(
            f"{'.'.join(str(loc) for loc in error['loc']) or '(root)'}: {error['msg']}"
            for error in exc.errors(include_url=False, include_input=False)
        )
    else:
        message = str(exc)
    message = " ".join(message.split())
    message = redact_secrets(message, secrets)
    if len(message) > MAX_MESSAGE_CHARS:
        message = message[:MAX_MESSAGE_CHARS] + "..."
    return f"{name}: {message}" if message else name
