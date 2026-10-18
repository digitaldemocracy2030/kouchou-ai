#!/usr/bin/env python3
"""公開レポートにユーザー API キーが漏れていないかを確認する。

PR #868 (2026-05-29 merge) から PR #1026 の修正までの間に生成・再集計されたレポートでは、
管理画面で入力した「ユーザー API キー」が hierarchical_result.json の
``config.user_api_key`` に平文で書き出されていた。公開ビューアはレポート全体を
クライアントに渡すため、ページの HTML にも埋め込まれる。

このスクリプトは標準ライブラリだけで動き、次のいずれかを対象にできる。

    # 公開ビューアのレポートページ URL（API キー不要）
    python check_report_secret_leak.py https://viewer.example.com/my-report

    # 公開 API。--all で公開中（ready かつ公開/限定公開）の全レポートを確認
    python check_report_secret_leak.py --api-base https://api.example.com --api-key <PUBLIC_API_KEY> --all
    python check_report_secret_leak.py --api-base https://api.example.com --api-key <PUBLIC_API_KEY> my-report

    # サーバー上のファイル / レポートディレクトリ
    python check_report_secret_leak.py path/to/hierarchical_result.json
    python check_report_secret_leak.py --report-dir path/to/outputs

キーは先頭と末尾の数文字だけを表示する。漏洩が 1 件でも見つかれば終了コード 1 を返す。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SECRET_KEYS = ("user_api_key",)
# HTML（Next.js の RSC payload）では JSON が JS 文字列に埋め込まれ、引用符が \" にエスケープされる
HTML_SECRET_RE = re.compile(r'user_api_key\\*"\s*:\s*\\*"([^"\\]*)')
HTML_PATH_RE = re.compile(r'_(?:output|input)_base_dir\\*"\s*:\s*\\*"([^"\\]*)')


@dataclass
class Finding:
    target: str
    leaked_keys: list[tuple[str, str]] = field(default_factory=list)  # (JSON パス, 値)
    internal_paths: list[tuple[str, str]] = field(default_factory=list)
    error: str | None = None

    @property
    def leaked(self) -> bool:
        return bool(self.leaked_keys)


def mask(value: str) -> str:
    if len(value) <= 10:
        return "*" * len(value)
    return f"{value[:4]}…{value[-4:]} (len={len(value)})"


def scan_json(obj: Any, finding: Finding, path: str = "$") -> None:
    if isinstance(obj, dict):
        for key, value in obj.items():
            child = f"{path}.{key}"
            if key in SECRET_KEYS and isinstance(value, str) and value:
                finding.leaked_keys.append((child, value))
            elif key in ("_output_base_dir", "_input_base_dir") and isinstance(value, str):
                finding.internal_paths.append((child, value))
            scan_json(value, finding, child)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            scan_json(item, finding, f"{path}[{i}]")


def scan_html(html: str, finding: Finding) -> None:
    for m in HTML_SECRET_RE.finditer(html):
        if m.group(1):
            finding.leaked_keys.append(("html:user_api_key", m.group(1)))
    for m in HTML_PATH_RE.finditer(html):
        finding.internal_paths.append(("html:_base_dir", m.group(1)))


def http_get(url: str, headers: dict[str, str] | None = None, timeout: float = 30) -> tuple[str, str]:
    req = urllib.request.Request(url, headers={"User-Agent": "kouchou-ai-leak-check/1.0", **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as res:
        content_type = res.headers.get("Content-Type", "")
        return res.read().decode("utf-8", errors="replace"), content_type


def check_url(url: str) -> Finding:
    finding = Finding(target=url)
    try:
        body, content_type = http_get(url)
    except (urllib.error.URLError, TimeoutError) as e:
        finding.error = str(e)
        return finding
    if "json" in content_type:
        try:
            scan_json(json.loads(body), finding)
            return finding
        except json.JSONDecodeError:
            pass
    scan_html(body, finding)
    return finding


def check_api_report(api_base: str, api_key: str, slug: str) -> Finding:
    url = f"{api_base.rstrip('/')}/reports/{urllib.parse.quote(slug)}"
    finding = Finding(target=url)
    try:
        body, _ = http_get(url, headers={"x-api-key": api_key})
        scan_json(json.loads(body), finding)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as e:
        finding.error = str(e)
    return finding


def list_api_reports(api_base: str, api_key: str) -> list[str]:
    body, _ = http_get(f"{api_base.rstrip('/')}/reports", headers={"x-api-key": api_key})
    return [r["slug"] for r in json.loads(body)]


def check_file(path: Path) -> Finding:
    finding = Finding(target=str(path))
    try:
        scan_json(json.loads(path.read_text(encoding="utf-8")), finding)
    except (OSError, json.JSONDecodeError) as e:
        finding.error = str(e)
    return finding


def report(findings: list[Finding], show_paths: bool) -> int:
    leaked = 0
    for f in findings:
        if f.error:
            print(f"[ERROR] {f.target}: {f.error}")
        elif f.leaked:
            leaked += 1
            print(f"[LEAK]  {f.target}")
            for path, value in dict.fromkeys(f.leaked_keys):
                print(f"          {path} = {mask(value)}")
        else:
            print(f"[OK]    {f.target}")
        if show_paths and f.internal_paths:
            for path, value in dict.fromkeys(f.internal_paths):
                print(f"          (内部パス) {path} = {value}")
    errors = sum(1 for f in findings if f.error)
    print(f"\n確認 {len(findings)} 件 / 漏洩あり {leaked} 件 / エラー {errors} 件")
    return 1 if leaked else (2 if errors else 0)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("targets", nargs="*", help="レポートページ URL / API の slug / JSON ファイルパス")
    parser.add_argument("--api-base", help="公開 API のベース URL（指定時、targets は slug として扱う）")
    parser.add_argument("--api-key", help="公開 API の x-api-key（PUBLIC_API_KEY）")
    parser.add_argument("--all", action="store_true", help="--api-base の公開レポート一覧を全件確認")
    parser.add_argument("--report-dir", type=Path, help="<report-dir>/<slug>/hierarchical_result.json を全件確認")
    parser.add_argument("--show-internal-paths", action="store_true", help="config に残るサーバー内部パスも表示")
    args = parser.parse_args(argv)

    findings: list[Finding] = []
    if args.api_base:
        if not args.api_key:
            parser.error("--api-base には --api-key が必要です")
        slugs = list(args.targets)
        if args.all:
            slugs += [s for s in list_api_reports(args.api_base, args.api_key) if s not in slugs]
        findings += [check_api_report(args.api_base, args.api_key, s) for s in slugs]
    else:
        for target in args.targets:
            if target.startswith(("http://", "https://")):
                findings.append(check_url(target))
            else:
                findings.append(check_file(Path(target)))
    if args.report_dir:
        findings += [check_file(p) for p in sorted(args.report_dir.glob("*/hierarchical_result.json"))]

    if not findings:
        parser.error("確認対象がありません")
    return report(findings, args.show_internal_paths)


if __name__ == "__main__":
    sys.exit(main())
