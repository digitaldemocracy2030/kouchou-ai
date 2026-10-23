"""
Utility functions for the analysis pipeline.

Migrated from apps/api/broadlistening/pipeline/utils.py
"""

import json
import os
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import polars as pl


def read_input_csv(path: str | Path, **kwargs: Any) -> pl.DataFrame:
    """Read user-provided input CSV columns as strings.

    Input metadata columns are categorical labels, not numeric measures. Keeping
    them as strings avoids Polars inferring a numeric dtype from early rows and
    then failing when later rows contain non-numeric labels.
    """
    kwargs.setdefault("infer_schema_length", 0)
    return pl.read_csv(path, **kwargs)


@contextmanager
def atomic_output_path(path: str | Path) -> Iterator[Path]:
    """同じディレクトリの一時ファイルのパスを渡し、ブロックが正常に終われば os.replace で差し替える。

    最終パスを open("w") で直接書くと先に空になり、書き込み中に読み手（公開 API など）が
    空・書きかけのファイルを読む。一時ファイル名にはプロセス内のスレッド間でも衝突しない
    よう pid と uuid を入れる。失敗したときは一時ファイルを消し、既存のファイルは残す。
    """
    path = Path(path)
    tmp_path = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex}.tmp")
    try:
        yield tmp_path
        os.replace(tmp_path, path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def write_json_atomic(path: str | Path, data: Any) -> None:
    """JSON を一時ファイルに書いてから os.replace し、読み手に書きかけを見せない。"""
    with atomic_output_path(path) as tmp_path:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)


def typed_message(t: str, m: str) -> dict[str, str]:
    """
    Convert a message type and content to OpenAI message format.

    Args:
        t: Message type ('system', 'human', or 'ai')
        m: Message content

    Returns:
        OpenAI-compatible message dictionary

    Raises:
        Exception: If message type is unknown
    """
    if t == "system":
        return {"role": "system", "content": m}
    if t == "human":
        return {"role": "user", "content": m}
    if t == "ai":
        return {"role": "assistant", "content": m}
    raise Exception(f"Unknown message type in prompt: {t}")


def messages(prompt: str, input_text: str) -> list[dict[str, str]]:
    """
    Parse a prompt template into OpenAI-compatible messages.

    The prompt format supports /system, /human, and /ai markers:
    ```
    /system
    You are a helpful assistant.

    /human
    Please analyze this text.
    ```

    Args:
        prompt: The prompt template with markers
        input_text: The user input to append

    Returns:
        List of OpenAI-compatible message dictionaries
    """
    lines = prompt.strip().splitlines()
    results: list[tuple[str, str]] = []
    t: str | None = None
    m = ""

    for line in lines:
        if line.startswith("/"):
            if t is not None:
                results.append((t, m))
            t = line[1:].strip()
            m = ""
        else:
            m += line + "\n"

    if t is not None:
        results.append((t, m))

    results.append(("human", input_text))

    return [typed_message(t, m) for (t, m) in results]


def format_token_count(count: int) -> str:
    """
    Format a token count for display.

    Args:
        count: Number of tokens

    Returns:
        Formatted string (e.g., "1.2K", "3.4M")
    """
    if count >= 1_000_000:
        return f"{count / 1_000_000:.1f}M"
    if count >= 1_000:
        return f"{count / 1_000:.1f}K"
    return str(count)


def estimate_tokens(text: str) -> int:
    """
    Estimate the number of tokens in a text.

    This is a rough estimate based on character count.
    For accurate counts, use the tokenizer for your model.

    Args:
        text: The text to estimate

    Returns:
        Estimated token count
    """
    # Rough estimate: ~4 characters per token for English
    # Japanese text is typically more tokens per character
    return len(text) // 4


def chunk_text(text: str, max_tokens: int = 4000, overlap: int = 200) -> list[str]:
    """
    Split text into chunks for processing.

    Args:
        text: Text to split
        max_tokens: Maximum tokens per chunk
        overlap: Token overlap between chunks

    Returns:
        List of text chunks
    """
    # Convert token limits to character estimates
    max_chars = max_tokens * 4
    overlap_chars = overlap * 4

    chunks: list[str] = []
    start = 0

    while start < len(text):
        end = start + max_chars
        if end >= len(text):
            chunks.append(text[start:])
            break

        # Try to break at a sentence or paragraph
        break_point = text.rfind("\n\n", start, end)
        if break_point == -1 or break_point <= start:
            break_point = text.rfind(". ", start, end)
        if break_point == -1 or break_point <= start:
            break_point = text.rfind(" ", start, end)
        if break_point == -1 or break_point <= start:
            break_point = end

        chunks.append(text[start:break_point])
        start = break_point - overlap_chars

    return chunks
