"""hierarchical_result.json のレポート本文を他言語に翻訳する CLI。

Usage:
    python -m analysis_core.translate --result outputs/<name>/hierarchical_result.json --languages en,ko
    kouchou-translate --result outputs/<name>/hierarchical_result.json --languages en --output translated.json

既定では意見グループ名・説明・概要・問い・イントロだけを翻訳し、意見本文は
`--include-arguments` を付けたときだけ翻訳する（意見は件数が多く費用が大きいため）。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from analysis_core.steps.hierarchical_translation import (
    DEFAULT_BATCH_SIZE,
    DEFAULT_WORKERS,
    RequestFn,
    TranslationError,
    build_translation_items,
    make_llm_request,
    merge_translations,
    translate_result,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kouchou-translate",
        description="広聴AIのレポート本文を他言語に翻訳し、hierarchical_result.json の translations に書き込む",
    )
    parser.add_argument("--result", "-r", type=Path, required=True, help="hierarchical_result.json のパス")
    parser.add_argument(
        "--languages",
        "-l",
        type=str,
        required=True,
        help="翻訳先の言語コード（カンマ区切り。例: en,ko）",
    )
    parser.add_argument("--output", "-o", type=Path, help="書き出し先（省略時は --result を上書き）")
    parser.add_argument("--provider", type=str, help="LLM プロバイダー（省略時は結果 JSON の config.provider）")
    parser.add_argument("--model", type=str, help="モデル名（省略時は結果 JSON の config.model）")
    parser.add_argument(
        "--local-llm-address",
        type=str,
        help="provider=local のときのアドレス（省略時は config.local_llm_address）",
    )
    parser.add_argument("--workers", type=int, default=DEFAULT_WORKERS, help="並列リクエスト数")
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE, help="1リクエストあたりの項目数")
    parser.add_argument("--timeout-seconds", type=int, help="1リクエストのタイムアウト秒")
    parser.add_argument(
        "--include-arguments",
        action="store_true",
        help="意見本文も翻訳する（件数分のリクエストが増えるので費用に注意）",
    )
    parser.add_argument("--dry-run", action="store_true", help="翻訳対象の件数を表示して終了する")
    return parser


def _parse_languages(raw: str) -> list[str]:
    languages = [lang.strip() for lang in raw.split(",") if lang.strip()]
    if not languages:
        raise ValueError("--languages に言語コードを指定してください（例: en,ko）")
    return languages


def run(args: argparse.Namespace, request: RequestFn | None = None) -> int:
    """CLI 本体。request を渡すと LLM 呼び出しを差し替えられる（テスト用）。"""
    if not args.result.exists():
        print(f"Error: Result file not found: {args.result}", file=sys.stderr)
        return 1
    languages = _parse_languages(args.languages)
    result: dict[str, Any] = json.loads(args.result.read_text(encoding="utf-8"))
    config = result.get("config") or {}

    items = build_translation_items(result, include_arguments=args.include_arguments)
    cluster_count = sum(1 for item in items if item["kind"] == "cluster")
    argument_count = sum(1 for item in items if item["kind"] == "argument")
    other_count = len(items) - cluster_count - argument_count
    print(f"Translation targets: clusters={cluster_count}, texts={other_count}, arguments={argument_count}")
    print(f"  Languages: {', '.join(languages)}")
    if args.dry_run:
        return 0

    provider = args.provider or config.get("provider") or "openai"
    model = args.model or config.get("model")
    if not model:
        print("Error: --model を指定してください（結果 JSON に config.model がありません）", file=sys.stderr)
        return 1
    usage: dict[str, int] = {}
    if request is None:
        request = make_llm_request(
            provider=provider,
            model=model,
            local_llm_address=args.local_llm_address or config.get("local_llm_address"),
            timeout_seconds=args.timeout_seconds,
            usage=usage,
        )
    print(f"  Provider: {provider}, Model: {model}")

    try:
        translations = translate_result(
            result,
            languages,
            request,
            include_arguments=args.include_arguments,
            batch_size=args.batch_size,
            workers=args.workers,
            meta={"provider": provider, "model": model},
        )
    except TranslationError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    output_path = args.output or args.result
    merged = merge_translations(result, translations)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote translations for {', '.join(languages)} to {output_path}")
    if usage:
        print(
            "Token usage: "
            f"input={usage.get('token_usage_input', 0)}, output={usage.get('token_usage_output', 0)}, "
            f"total={usage.get('total_token_usage', 0)}"
        )
    return 0


def main(argv: list[str] | None = None, request: RequestFn | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return run(args, request=request)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
