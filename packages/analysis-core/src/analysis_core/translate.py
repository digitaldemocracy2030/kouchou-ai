"""hierarchical_result.json のレポート本文を他言語に翻訳する CLI。

Usage:
    python -m analysis_core.translate --result outputs/<name>/hierarchical_result.json --languages en,ko
    kouchou-translate --result outputs/<name>/hierarchical_result.json --languages en --output translated.json

既定では意見グループ名・説明・概要・問い・イントロだけを翻訳し、意見本文は
`--include-arguments` を付けたときだけ翻訳する（意見は件数が多く費用が大きいため）。

--result を上書きするときは、同じディレクトリの translations.json にも訳を残す。集計
（意見グループ名の編集後の再集計など）は hierarchical_result.json を作り直すので、訳は
translations.json から読み直される。原文が変わった項目の訳は、そのとき落とされる。

LLM の鍵は環境変数（サーバーの既定の鍵）だけを使う。結果 JSON の config に残った
user_api_key は読まず、書き戻すときに config から取り除く。
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from analysis_core.steps.hierarchical_translation import (
    DEFAULT_BATCH_SIZE,
    DEFAULT_WORKERS,
    SOURCE_HASHES_KEY,
    TRANSLATIONS_FILENAME,
    RequestFn,
    TranslationError,
    build_translation_items,
    make_llm_request,
    merge_translations,
    source_hashes,
    translate_result,
    without_source_hashes,
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


def _pipeline_running(result_path: Path) -> bool:
    """同じレポートで分析・再集計が実行中か（hierarchical_status.json が running で、ロックが切れていない）。"""
    status_path = result_path.parent / "hierarchical_status.json"
    try:
        status = json.loads(status_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    if not isinstance(status, dict) or status.get("status") != "running":
        return False
    try:
        return datetime.fromisoformat(str(status.get("lock_until"))) > datetime.now()
    except ValueError:
        return False


def _read_result(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_outputs(
    args: argparse.Namespace,
    result: dict[str, Any],
    translations: dict[str, dict[str, Any]],
) -> Path:
    """訳を書き出す。--result の上書きなら translations.json にも残す。どちらも一時ファイルから差し替える。"""
    from analysis_core.core.utils import write_json_atomic
    from analysis_core.steps.hierarchical_aggregation import _public_config

    output_path: Path = args.output or args.result
    in_place = output_path.resolve() == args.result.resolve()
    if in_place:
        store_path = args.result.parent / TRANSLATIONS_FILENAME
        try:
            stored = json.loads(store_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            stored = {}
        if not isinstance(stored, dict):
            stored = {}
        stored.update(translations)
        write_json_atomic(store_path, stored)

    merged = merge_translations(result, without_source_hashes(translations))
    merged["translations"] = without_source_hashes(merged["translations"])
    # 修正前の版で作った結果 JSON の config には user_api_key などが残っていることがある。集計と同じく取り除く
    if isinstance(merged.get("config"), dict):
        merged["config"] = _public_config(merged["config"])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    write_json_atomic(output_path, merged)
    return output_path


def run(args: argparse.Namespace, request: RequestFn | None = None) -> int:
    """CLI 本体。request を渡すと LLM 呼び出しを差し替えられる（テスト用）。"""
    if not args.result.exists():
        print(f"Error: Result file not found: {args.result}", file=sys.stderr)
        return 1
    languages = _parse_languages(args.languages)
    result: dict[str, Any] = _read_result(args.result)
    config = result.get("config") or {}

    items = build_translation_items(result, include_arguments=args.include_arguments)
    cluster_count = sum(1 for item in items if item["kind"] == "cluster")
    argument_count = sum(1 for item in items if item["kind"] == "argument")
    other_count = len(items) - cluster_count - argument_count
    print(f"Translation targets: clusters={cluster_count}, texts={other_count}, arguments={argument_count}")
    print(f"  Languages: {', '.join(languages)}")
    if args.dry_run:
        return 0

    if _pipeline_running(args.result):
        print(
            "Error: このレポートは分析・再集計の実行中です。終わってから実行してください（結果は書き換えていません）",
            file=sys.stderr,
        )
        return 1

    provider = args.provider or config.get("provider") or "openai"
    model = args.model or config.get("model")
    if not model:
        print("Error: --model を指定してください（結果 JSON に config.model がありません）", file=sys.stderr)
        return 1
    usage: dict[str, int] = {}
    if request is None:
        # 鍵は環境変数から取る。結果 JSON の config.user_api_key は読まない
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

    # 翻訳の間に、管理画面の編集などで結果が作り直されていたら書かない。
    # 開始時の内容で丸ごと書き戻すと編集を巻き戻し、古い原文から作った訳が新しい原文に付いてしまう。
    try:
        current = _read_result(args.result)
    except (OSError, json.JSONDecodeError) as exc:
        print(f"Error: 書き戻す前に結果 JSON を読み直せませんでした（{exc}）。何も書き換えていません", file=sys.stderr)
        return 1
    if build_translation_items(current, include_arguments=args.include_arguments) != items or _pipeline_running(
        args.result
    ):
        print(
            "Error: 翻訳の間にレポートの内容が更新されました（意見グループ名の編集・再集計など）。"
            "何も書き換えていません。もう一度実行してください",
            file=sys.stderr,
        )
        return 1

    hashes = source_hashes(items)
    for entry in translations.values():
        entry["meta"][SOURCE_HASHES_KEY] = hashes

    output_path = _write_outputs(args, current, translations)
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
