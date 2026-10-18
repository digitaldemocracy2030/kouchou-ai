"""メンテナー専用のコメントコマンドに、コメント投稿者の権限チェックが付いているかを確認する。

使い方: python scripts/check_comment_commands.py

/ready・/archive は GitHub App のトークンで org Project の Status を書き換えるので、
リポジトリのメンテナー（OWNER / MEMBER / COLLABORATOR）のコメントだけで実行する。
誰でも使ってよい /assign などはここでは扱わない。PyYAML に依存しない簡易チェック。
"""

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# ワークフローファイル → メンテナー専用のコマンド
MAINTAINER_ONLY_COMMANDS = {
    ".github/workflows/status-update-command.yml": ["/ready", "/archive"],
}
ALLOWED_ASSOCIATIONS = {"OWNER", "MEMBER", "COLLABORATOR"}

IF_LINE = re.compile(r"^\s*if:\s*(.+)$")
ASSOCIATION_CHECK = re.compile(
    r"contains\(\s*fromJSON\('(\[[^']*\])'\)\s*,\s*github\.event\.comment\.author_association\s*\)"
)


def check_workflow(rel: str, commands: list[str]) -> list[str]:
    text = (REPO_ROOT / rel).read_text(encoding="utf-8")
    errors = []
    found = False
    for line in text.splitlines():
        match = IF_LINE.match(line)
        if not match or not any(f"'{cmd}'" in match.group(1) for cmd in commands):
            continue
        found = True
        check = ASSOCIATION_CHECK.search(match.group(1))
        if not check:
            errors.append(
                f"{rel}: コマンドの if 条件に author_association のチェックがない: {match.group(1)}"
            )
            continue
        allowed = set(re.findall(r'"([A-Z_]+)"', check.group(1)))
        if not allowed or not allowed <= ALLOWED_ASSOCIATIONS:
            errors.append(
                f"{rel}: author_association の許可リスト {sorted(allowed)} がメンテナー以外を含む"
            )
    if not found:
        errors.append(f"{rel}: {commands} を判定する if 条件が見つからない")
    return errors


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    errors = []
    for rel, commands in MAINTAINER_ONLY_COMMANDS.items():
        errors.extend(check_workflow(rel, commands))
    if errors:
        print("\n".join(errors))
        return 1
    print("OK: comment commands")
    return 0


if __name__ == "__main__":
    sys.exit(main())
