"""
Utility functions for the analysis pipeline.

Migrated from apps/api/broadlistening/pipeline/utils.py
"""

from typing import Any


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
