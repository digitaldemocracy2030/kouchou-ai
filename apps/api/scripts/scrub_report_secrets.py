#!/usr/bin/env python3
"""既存レポートの hierarchical_result.json から非公開キーを取り除く（レポートは温存）。

PR #868 (2026-05-29 merge) から PR #1026 の修正までの間に生成・再集計されたレポートでは、
``config.user_api_key``（管理画面で入力したユーザー API キー）、サーバー内部パス
（``_output_base_dir`` などの ``_`` 始まりのキー）、前回 status の ``error_stack_trace`` が
hierarchical_result.json に書き出されていた。

このスクリプトは ``config`` 配下からそれらのキーだけを再帰的に削除し、意見・クラスタ・ラベル・
概要などレポートの中身には触れない。再生成や LLM の再実行は行わない。

API サーバーのコンテナ（作業ディレクトリ apps/api）で実行する想定:

    # 1. 確認だけ（既定。ファイルは変更しない）
    python scripts/scrub_report_secrets.py

    # 2. 修正する。元ファイルは --backup-dir に退避（キーを含むので扱いに注意）
    python scripts/scrub_report_secrets.py --apply --backup-dir /secure/place

    # 3. 修正後のファイルをストレージ（Azure Blob 等）へ上書きし、公開ビューアのキャッシュを破棄
    python scripts/scrub_report_secrets.py --apply --backup-dir /secure/place --sync-storage --revalidate

--report-dir を省略すると、API の設定（src.config.settings.REPORT_DIR）を使う。
--slug で対象を絞れる（複数指定可）。

注意:
- ストレージを使う構成では、起動時にストレージからレポートをダウンロードする。
  --sync-storage を付けないと、再起動時に修正前のファイルで上書きされる。
- 静的書き出し（ZIP）や管理画面からダウンロード済みの JSON は、このスクリプトでは直せない。
- 漏れたキーそのものは、利用者に無効化・再発行してもらう必要がある。
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

NON_PUBLIC_CONFIG_KEYS = {"user_api_key", "error_stack_trace"}
RESULT_FILE = "hierarchical_result.json"
REMOTE_REPORT_DIR_PREFIX = "outputs"  # src.services.report_sync.ReportSyncService と同じ


def _is_non_public(key: Any) -> bool:
    return isinstance(key, str) and (key.startswith("_") or key in NON_PUBLIC_CONFIG_KEYS)


def scrub_config(obj: Any, path: str = "config") -> tuple[Any, list[str]]:
    """非公開キーを除いたコピーと、削除したキーの JSON パス一覧を返す。"""
    removed: list[str] = []
    if isinstance(obj, dict):
        cleaned = {}
        for key, value in obj.items():
            child = f"{path}.{key}"
            if _is_non_public(key):
                removed.append(child)
                continue
            cleaned[key], sub = scrub_config(value, child)
            removed += sub
        return cleaned, removed
    if isinstance(obj, list):
        cleaned_list = []
        for i, item in enumerate(obj):
            cleaned_item, sub = scrub_config(item, f"{path}[{i}]")
            cleaned_list.append(cleaned_item)
            removed += sub
        return cleaned_list, removed
    return obj, removed


def scrub_result(result: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """result の config だけを書き換える。config 以外のキーと順序はそのまま。"""
    config = result.get("config")
    if not isinstance(config, dict):
        return result, []
    cleaned, removed = scrub_config(config)
    if not removed:
        return result, []
    return {**result, "config": cleaned}, removed


def _atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.chmod(tmp, path.stat().st_mode & 0o777)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def _default_report_dir() -> Path | None:
    try:
        sys.path.insert(0, str(Path.cwd()))
        from src.config import settings  # type: ignore

        return Path(settings.REPORT_DIR)
    except Exception:
        return None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--report-dir", type=Path, help="レポートの親ディレクトリ（<dir>/<slug>/hierarchical_result.json）"
    )
    parser.add_argument("--slug", action="append", default=[], help="対象 slug（複数指定可。省略時は全件）")
    parser.add_argument("--apply", action="store_true", help="実際に書き換える（省略時は確認のみ）")
    parser.add_argument("--backup-dir", type=Path, help="--apply 時の元ファイル退避先（レポートディレクトリの外）")
    parser.add_argument("--no-backup", action="store_true", help="退避せずに書き換える")
    parser.add_argument("--sync-storage", action="store_true", help="修正後のファイルを API のストレージへ上書き")
    parser.add_argument("--revalidate", action="store_true", help="公開ビューアのキャッシュを破棄（REVALIDATE_URL）")
    args = parser.parse_args(argv)

    report_dir = args.report_dir or _default_report_dir()
    if report_dir is None or not report_dir.is_dir():
        parser.error("--report-dir を指定してください（API の設定から REPORT_DIR を取得できませんでした）")
    report_dir = report_dir.resolve()

    if args.apply and not args.no_backup:
        if args.backup_dir is None:
            parser.error("--apply には --backup-dir（または --no-backup）が必要です")
        backup_root = args.backup_dir.resolve()
        if backup_root == report_dir or report_dir in backup_root.parents:
            # レポートディレクトリ内の .json はストレージ同期の対象になるため、キー入りの退避ファイルを置かない
            parser.error("--backup-dir はレポートディレクトリの外にしてください")
        backup_root = backup_root / datetime.now().strftime("%Y%m%d-%H%M%S")

    if (args.sync_storage or args.revalidate) and not args.apply:
        parser.error("--sync-storage / --revalidate は --apply と一緒に指定してください")

    storage = None
    invalidate = None
    if args.sync_storage:
        from src.services.storage import get_storage_service  # type: ignore

        storage = get_storage_service()
    if args.revalidate:
        from src.services.report_status import invalidate_report_cache  # type: ignore

        invalidate = invalidate_report_cache

    paths = (
        [report_dir / s / RESULT_FILE for s in args.slug] if args.slug else sorted(report_dir.glob(f"*/{RESULT_FILE}"))
    )

    affected = 0
    failed = 0
    for path in paths:
        slug = path.parent.name
        try:
            result = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            print(f"[ERROR] {slug}: 読み込めません: {e}")
            failed += 1
            continue
        cleaned, removed = scrub_result(result)
        if not removed:
            print(f"[OK]    {slug}")
            continue
        affected += 1
        has_key = any(p.endswith(".user_api_key") for p in removed)
        label = "LEAK " if has_key else "PATH "
        print(f"[{label}] {slug}: {', '.join(removed)}")
        if not args.apply:
            continue
        try:
            if not args.no_backup:
                dest = backup_root / slug / RESULT_FILE
                dest.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
                shutil.copy2(path, dest)
                os.chmod(dest, 0o600)
            _atomic_write_json(path, cleaned)
            print("          -> 修正済み")
            if storage is not None:
                remote = f"{REMOTE_REPORT_DIR_PREFIX}/{slug}/{RESULT_FILE}"
                if storage.upload_file(str(path), remote) is False:
                    raise RuntimeError(f"ストレージへのアップロードに失敗: {remote}")
                print(f"          -> ストレージへ反映: {remote}")
            if invalidate is not None:
                invalidate(slug)
                print("          -> キャッシュ破棄を要求")
        except Exception as e:
            print(f"[ERROR] {slug}: {e}")
            failed += 1

    mode = "修正" if args.apply else "確認のみ（--apply で修正）"
    print(f"\n{mode}: 対象 {len(paths)} 件 / 要修正 {affected} 件 / エラー {failed} 件")
    if args.apply and not args.no_backup and affected:
        print(f"元ファイルの退避先: {backup_root}（API キーを含むため、確認後に安全に削除してください）")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
