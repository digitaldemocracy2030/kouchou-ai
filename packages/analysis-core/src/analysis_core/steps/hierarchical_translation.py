"""レポート本文（意見グループ名・説明・概要など）を LLM で他言語に翻訳する。

`hierarchical_result.json` の `translations` に、言語コードごとの訳を書き込む。
public-viewer は表示言語に対応する訳があれば本文を差し替え、無ければ元の言語で表示する。

translations の形:

    {
      "en": {
        "clusters": {"<cluster id>": {"label": "...", "takeaway": "..."}},
        "overview": "...",
        "question": "...",
        "intro": "...",
        "arguments": {"<arg_id>": "..."},   # --include-arguments のときだけ
        "meta": {"model": "...", "provider": "...", "generated_at": "..."}
      }
    }

このモジュールは import 時に標準ライブラリしか読まない。LLM 呼び出しは
`request` 引数（messages と json_schema を受け取り応答文字列を返す関数）として
外から渡すので、テストやスタンドアロンのスクリプトから依存なしに使える。
実際の LLM 呼び出しは `make_llm_request` が `services.llm.request_to_chat_ai` を包んで作る。
"""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from typing import Any

LANGUAGE_NAMES = {
    "ja": "日本語",
    "en": "英語 (English)",
    "ko": "韓国語 (한국어)",
    "zh": "中国語 (中文)",
    "zh-tw": "繁体字中国語 (繁體中文)",
    "es": "スペイン語 (Español)",
    "fr": "フランス語 (Français)",
    "de": "ドイツ語 (Deutsch)",
    "pt": "ポルトガル語 (Português)",
    "vi": "ベトナム語 (Tiếng Việt)",
    "th": "タイ語 (ภาษาไทย)",
    "id": "インドネシア語 (Bahasa Indonesia)",
}

TRANSLATION_PROMPT = """あなたは市民の意見を分析したレポートの翻訳者です。
入力は JSON で、items の各要素は id・kind・texts（翻訳対象の文字列の配列）を持ちます。
すべての texts を{language}に翻訳し、同じ id、同じ要素数、同じ順序で返してください。

# 指示
- 意味を変えず、要約・省略・補足をしない
- 固有名詞・数値・記号・URL はそのまま保つ
- kind が cluster の場合、texts[0] は意見グループの見出し、texts[1] はその説明文。見出しは短く自然な表現にする
- kind が overview / question / intro / argument の場合、texts[0] は本文。文体は元の文に合わせる
- 翻訳文以外（注釈・説明・原文）は出力しない
- 出力は JSON のみ: {{"items": [{{"id": "...", "texts": ["..."]}}]}}
"""

DEFAULT_BATCH_SIZE = 10

# レポートの出力ディレクトリに置く訳の保存先。集計（hierarchical_aggregation）は
# hierarchical_result.json を毎回作り直すので、訳はここから読み直して結果に入れる。
TRANSLATIONS_FILENAME = "translations.json"
# translations.json の各言語の meta に、訳の元になった原文の指紋（項目 id → ハッシュ）を残すキー。
# 集計はこれと今の原文を比べ、編集で原文が変わった項目の古い訳を捨てる。結果 JSON には書かない。
SOURCE_HASHES_KEY = "source_hashes"
DEFAULT_WORKERS = 2

# OpenAI の json_schema 形式。services.llm は dict をそのまま response_format に渡し、
# Gemini 用には内側の schema を取り出すので、各プロバイダで共通に使える。
TRANSLATION_SCHEMA: dict[str, Any] = {
    "type": "json_schema",
    "json_schema": {
        "name": "TranslationBatch",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "id": {"type": "string"},
                            "texts": {"type": "array", "items": {"type": "string"}},
                        },
                        "required": ["id", "texts"],
                        "additionalProperties": False,
                    },
                }
            },
            "required": ["items"],
            "additionalProperties": False,
        },
    },
}

RequestFn = Callable[[list[dict[str, str]], dict[str, Any]], Any]


class TranslationError(RuntimeError):
    """翻訳に失敗した項目がある。原文は含めず id だけを示す（#915 のラベル失敗と同じ方針）。"""

    def __init__(self, language: str, failures: dict[str, str]):
        self.language = language
        self.failures = failures
        details = ", ".join(f"{item_id} ({kind})" for item_id, kind in failures.items())
        super().__init__(
            f"translation ({language}): {len(failures)}件の翻訳に失敗しました。項目: {details}。処理を中止しました。"
        )


def language_name(code: str) -> str:
    """プロンプトに書く言語名。未知のコードはコードのまま渡す。"""
    return LANGUAGE_NAMES.get(code.lower(), code)


def build_translation_items(result: dict[str, Any], include_arguments: bool = False) -> list[dict[str, Any]]:
    """結果 JSON から翻訳対象を取り出す。空文字は翻訳しない（訳も空にする）。"""
    items: list[dict[str, Any]] = []
    for cluster in result.get("clusters", []):
        items.append(
            {
                "id": f"cluster:{cluster['id']}",
                "kind": "cluster",
                "texts": [str(cluster.get("label") or ""), str(cluster.get("takeaway") or "")],
            }
        )
    config = result.get("config") or {}
    for kind, text in (
        ("overview", result.get("overview")),
        ("question", config.get("question")),
        ("intro", config.get("intro")),
    ):
        if text:
            items.append({"id": kind, "kind": kind, "texts": [str(text)]})
    if include_arguments:
        for argument in result.get("arguments", []):
            text = argument.get("argument")
            if text:
                items.append({"id": f"argument:{argument['arg_id']}", "kind": "argument", "texts": [str(text)]})
    return items


def chunked(items: list[Any], size: int) -> Iterable[list[Any]]:
    size = max(1, int(size))
    for start in range(0, len(items), size):
        yield items[start : start + size]


def _strip_think(text: str) -> str:
    # Reasoning モデルが出力する <think>…</think> を除く（hierarchical_overview と同じ扱い）
    return re.sub(r"<think\b[^>]*>.*?</think>", "", text, flags=re.DOTALL).strip()


def parse_translation_response(response: Any) -> dict[str, list[str]]:
    """応答を {id: texts} に直す。形が崩れていれば ValueError。"""
    data = response
    if isinstance(data, str):
        text = _strip_think(data)
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            # 前後に説明が付いた場合に備えて最初の { から最後の } までを試す
            start, end = text.find("{"), text.rfind("}")
            if start < 0 or end <= start:
                raise ValueError("translation response is not JSON") from None
            data = json.loads(text[start : end + 1])
    if isinstance(data, dict) and isinstance(data.get("items"), list):
        entries = data["items"]
    elif isinstance(data, list):
        entries = data
    else:
        raise ValueError("translation response has no items")
    parsed: dict[str, list[str]] = {}
    for entry in entries:
        if not isinstance(entry, dict) or not isinstance(entry.get("id"), str):
            continue
        texts = entry.get("texts")
        if isinstance(texts, str):
            texts = [texts]
        if not isinstance(texts, list) or not all(isinstance(t, str) for t in texts):
            continue
        parsed[entry["id"]] = texts
    return parsed


def _valid_translation(item: dict[str, Any], texts: list[str] | None) -> list[str] | None:
    """元の texts と同じ長さで、元が空でない箇所は訳も空でないことを確認する。"""
    if texts is None or len(texts) != len(item["texts"]):
        return None
    cleaned = [t.strip() for t in texts]
    for original, translated in zip(item["texts"], cleaned, strict=True):
        if original.strip() and not translated:
            return None
    # 元が空の箇所は訳も空にそろえる
    return [t if original.strip() else "" for original, t in zip(item["texts"], cleaned, strict=True)]


def _build_messages(items: list[dict[str, Any]], language: str) -> list[dict[str, str]]:
    payload = {"items": [{"id": i["id"], "kind": i["kind"], "texts": i["texts"]} for i in items]}
    return [
        {"role": "system", "content": TRANSLATION_PROMPT.format(language=language_name(language))},
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
    ]


def translate_items(
    items: list[dict[str, Any]],
    language: str,
    request: RequestFn,
    *,
    batch_size: int = DEFAULT_BATCH_SIZE,
    workers: int = DEFAULT_WORKERS,
) -> dict[str, list[str]]:
    """項目をバッチで翻訳する。

    1回目はバッチ単位で送り、欠けた・形が崩れた項目だけを1件ずつ再送する。
    それでも失敗した項目があれば TranslationError（id と失敗種別のみ）。
    """
    translated: dict[str, list[str]] = {}
    failures: dict[str, str] = {}
    targets = [item for item in items if any(t.strip() for t in item["texts"])]
    target_ids = {item["id"] for item in targets}
    for item in items:
        if item["id"] not in target_ids:
            translated[item["id"]] = ["" for _ in item["texts"]]

    def run_batch(batch: list[dict[str, Any]]) -> tuple[dict[str, list[str]], dict[str, str]]:
        ok: dict[str, list[str]] = {}
        failed: dict[str, str] = {}
        try:
            parsed = parse_translation_response(request(_build_messages(batch, language), TRANSLATION_SCHEMA))
        except Exception as exc:  # 失敗種別だけ残して続行し、最後にまとめて報告する
            kind = "invalid_response" if isinstance(exc, (ValueError, json.JSONDecodeError)) else type(exc).__name__
            if isinstance(exc, TimeoutError) or "timeout" in kind.lower():
                kind = "timeout"
            return ok, dict.fromkeys((item["id"] for item in batch), kind)
        for item in batch:
            texts = _valid_translation(item, parsed.get(item["id"]))
            if texts is None:
                failed[item["id"]] = "missing" if item["id"] not in parsed else "invalid_response"
            else:
                ok[item["id"]] = texts
        return ok, failed

    def run_all(batches: list[list[dict[str, Any]]]) -> dict[str, str]:
        pending: dict[str, str] = {}
        with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
            for ok, failed in executor.map(run_batch, batches):
                translated.update(ok)
                pending.update(failed)
        return pending

    pending = run_all(list(chunked(targets, batch_size)))
    if pending:
        retry = [item for item in targets if item["id"] in pending]
        failures = run_all([[item] for item in retry])
    if failures:
        raise TranslationError(language, failures)
    return translated


def assemble_translation(items: list[dict[str, Any]], translated: dict[str, list[str]]) -> dict[str, Any]:
    """{id: texts} を translations[lang] の形に組み立てる。"""
    entry: dict[str, Any] = {}
    clusters: dict[str, dict[str, str]] = {}
    arguments: dict[str, str] = {}
    for item in items:
        texts = translated.get(item["id"])
        if texts is None:
            continue
        kind = item["kind"]
        if kind == "cluster":
            clusters[item["id"].split(":", 1)[1]] = {"label": texts[0], "takeaway": texts[1]}
        elif kind == "argument":
            arguments[item["id"].split(":", 1)[1]] = texts[0]
        else:
            entry[kind] = texts[0]
    if clusters:
        entry["clusters"] = clusters
    if arguments:
        entry["arguments"] = arguments
    return entry


def translate_result(
    result: dict[str, Any],
    languages: list[str],
    request: RequestFn,
    *,
    include_arguments: bool = False,
    batch_size: int = DEFAULT_BATCH_SIZE,
    workers: int = DEFAULT_WORKERS,
    meta: dict[str, Any] | None = None,
) -> dict[str, dict[str, Any]]:
    """結果 JSON を各言語に翻訳し、{lang: translation} を返す（result は変更しない）。"""
    items = build_translation_items(result, include_arguments=include_arguments)
    translations: dict[str, dict[str, Any]] = {}
    for language in languages:
        translated = translate_items(items, language, request, batch_size=batch_size, workers=workers)
        entry = assemble_translation(items, translated)
        entry["meta"] = {
            **(meta or {}),
            "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "include_arguments": include_arguments,
        }
        translations[language] = entry
    return translations


def _text_hash(texts: list[str]) -> str:
    return hashlib.sha256(json.dumps(texts, ensure_ascii=False).encode("utf-8")).hexdigest()[:16]


def source_hashes(items: list[dict[str, Any]]) -> dict[str, str]:
    """翻訳対象の項目 id → 原文の指紋。原文が変わったかどうかの判定に使う。"""
    return {item["id"]: _text_hash(item["texts"]) for item in items}


def without_source_hashes(translations: dict[str, Any]) -> dict[str, Any]:
    """結果 JSON に書く形（meta から原文の指紋を除いたもの）を返す。"""
    public: dict[str, Any] = {}
    for language, entry in translations.items():
        if isinstance(entry, dict) and isinstance(entry.get("meta"), dict) and SOURCE_HASHES_KEY in entry["meta"]:
            entry = {**entry, "meta": {k: v for k, v in entry["meta"].items() if k != SOURCE_HASHES_KEY}}
        public[language] = entry
    return public


def fresh_translations(stored: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    """translations.json の訳のうち、今の結果の原文から作られたものだけを結果 JSON の形で返す。

    meta に原文の指紋が無い言語（手で置いた旧来の translations.json など）は、そのまま返す。
    指紋がある言語は、原文が変わった項目・無くなった項目の訳を落とす（編集後に古い訳を出さないため）。
    """
    current = source_hashes(build_translation_items(result, include_arguments=True))
    fresh: dict[str, Any] = {}
    for language, entry in stored.items():
        meta = entry.get("meta") if isinstance(entry, dict) else None
        hashes = meta.get(SOURCE_HASHES_KEY) if isinstance(meta, dict) else None
        if not isinstance(hashes, dict):
            fresh[language] = entry
            continue

        def is_fresh(item_id: str) -> bool:
            return item_id in current and hashes.get(item_id) == current[item_id]

        kept: dict[str, Any] = {}
        clusters = {
            cluster_id: value
            for cluster_id, value in (entry.get("clusters") or {}).items()
            if is_fresh(f"cluster:{cluster_id}")
        }
        if clusters:
            kept["clusters"] = clusters
        for kind in ("overview", "question", "intro"):
            if kind in entry and is_fresh(kind):
                kept[kind] = entry[kind]
        arguments = {
            arg_id: value for arg_id, value in (entry.get("arguments") or {}).items() if is_fresh(f"argument:{arg_id}")
        }
        if arguments:
            kept["arguments"] = arguments
        if kept:
            kept["meta"] = {k: v for k, v in meta.items() if k != SOURCE_HASHES_KEY}
            fresh[language] = kept
    return fresh


def merge_translations(result: dict[str, Any], translations: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """既存の translations を保ちつつ新しい言語を足した結果 JSON のコピーを返す。"""
    existing = result.get("translations")
    merged = dict(existing) if isinstance(existing, dict) else {}
    merged.update(translations)
    return {**result, "translations": merged}


def make_llm_request(
    *,
    provider: str,
    model: str,
    local_llm_address: str | None = None,
    timeout_seconds: int | None = None,
    usage: dict[str, int] | None = None,
) -> RequestFn:
    """services.llm.request_to_chat_ai を RequestFn に包む。トークン使用量は usage に足し込む。"""
    from analysis_core.services.llm import request_to_chat_ai
    from analysis_core.services.timeouts import DEFAULT_REQUEST_TIMEOUT_SECONDS
    from analysis_core.steps._labelling import record_usage

    timeout = timeout_seconds or DEFAULT_REQUEST_TIMEOUT_SECONDS

    def request(messages: list[dict[str, str]], json_schema: dict[str, Any]) -> Any:
        response, token_input, token_output, token_total = request_to_chat_ai(
            messages=messages,
            model=model,
            json_schema=json_schema,
            provider=provider,
            local_llm_address=local_llm_address,
            timeout_seconds=timeout,
        )
        if usage is not None:
            record_usage(usage, token_input, token_output, token_total)
        return response

    return request
