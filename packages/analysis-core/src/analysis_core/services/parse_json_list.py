import json
import re

COMMA_AND_SPACE_AND_RIGHT_BRACKET = re.compile(r",\s*(\])")

TEST = """Response was: 以下は、提供されたテキストの要約です。

[
  "創作文化は…",
  "生成AIは無断で特徴を抽出…",
  "多くのクリエイターは…",
  "生成AIによるコンテンツは…"
]"""


def parse_response(response):
    """
    指定されたレスポンス文字列からJSON配列を安全に抽出し、パースする。

    以下はdoctestによるテスト例。

    >>> parse_response('以下は...\\n```json\\n["a", "b"]\\n```')
    ['a', 'b']

    >>> parse_response('Response was: なんか説明\\n[ "x", "y" ] さらに何か')
    ['x', 'y']

    >>> parse_response('No json here')
    Traceback (most recent call last):
    ...
    RuntimeError: JSON list not found

    >>> parse_response('["a", "b" , ]')
    ['a', 'b']

    >>> parse_response(TEST)
    ['創作文化は…', '生成AIは無断で特徴を抽出…', '多くのクリエイターは…', '生成AIによるコンテンツは…']

    >>> parse_response('"a"')
    ['a']
    """
    try:
        obj = json.loads(response)
        if isinstance(obj, str):
            obj = [obj]
        items = [a.strip() for a in obj if a.strip()]
        return items
    except Exception:
        # 不要なコードブロックを除去
        response = response.replace("```json", "").replace("```", "")

        # JSON配列部分を抽出
        match = re.search(r"\[.*?\]", response, flags=re.DOTALL)
        if not match:
            # JSON配列が見つからなければraise
            raise RuntimeError("JSON list not found") from None

        json_str = match.group(0)
        # ", ]" のようなパターンを "]" に置換
        json_str = COMMA_AND_SPACE_AND_RIGHT_BRACKET.sub(r"\1", json_str)

        obj = json.loads(json_str)  # ここでも例外の場合はそのまま外に投げる
        if isinstance(obj, str):
            obj = [obj]
        try:
            items = [a.strip() for a in obj]
        except Exception as e:
            print("Error:", e)
            print("Input was:", json_str)
            print("Response was:", response)
            print("JSON was:", obj)
            print("skip")
            items = []
        return items


def parse_extraction_response(response: str | dict) -> list[str]:
    """Parse a valid extraction response; malformed output is not an empty result."""
    try:
        data = json.loads(response) if isinstance(response, str) else response
    except json.JSONDecodeError:
        raise ValueError("Invalid extraction response: malformed JSON") from None
    if not isinstance(data, dict):
        raise ValueError("Invalid extraction response: expected an object")
    items = data.get("extractedOpinionList")
    if not isinstance(items, list) or not all(isinstance(item, str) for item in items):
        raise ValueError("Invalid extraction response: expected extractedOpinionList to be a list of strings")
    return items


if __name__ == "__main__":
    import doctest

    doctest.testmod(verbose=True)
