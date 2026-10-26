"""メンテナー専用のコメントコマンドに、コメント投稿者の権限チェックが付いているかを確認する。

使い方: python scripts/check_comment_commands.py

/ready・/archive は GitHub App のトークンで org Project の Status を書き換えるので、
リポジトリのメンテナー（OWNER / MEMBER / COLLABORATOR）のコメントだけで実行する。
誰でも使ってよい /assign などはここでは扱わない。PyYAML に依存しない簡易チェック。
"""

import json
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
# if 条件の全体が「(コマンドの判定) && contains(fromJSON('[...]'), github.event.comment.author_association)」
# の形であることを求める。|| で権限チェックを迂回できる形を通さない
GUARDED_CONDITION = re.compile(
    r"^\((?P<commands>.*)\)\s*&&\s*"
    r"contains\(\s*fromJSON\('(?P<allowed>\[[^']*\])'\)\s*,\s*github\.event\.comment\.author_association\s*\)$"
)


def _wraps_whole(text: str) -> bool:
    """text の先頭の '(' に対応する ')' が末尾にある（括弧の外に || などが無い）かを返す。"""
    depth = 0
    for i, ch in enumerate(text):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return i == len(text) - 1
    return False


def check_condition(condition: str) -> str | None:
    """メンテナー専用コマンドの if 条件を検査し、問題があれば理由を返す。"""
    condition = condition.strip()
    match = GUARDED_CONDITION.match(condition)
    if not match or not _wraps_whole(f"({match.group('commands')})"):
        return (
            "if 条件が「(コマンドの判定) && contains(fromJSON('[...]'), "
            "github.event.comment.author_association)」の形になっていない"
        )
    if "contains(" in match.group("commands") or "author_association" in match.group(
        "commands"
    ):
        return "コマンドの判定の中に権限チェックが混ざっている"
    try:
        allowed = json.loads(match.group("allowed"))
    except ValueError:
        return f"author_association の許可リストを JSON として読めない: {match.group('allowed')}"
    if (
        not isinstance(allowed, list)
        or not allowed
        or not all(isinstance(v, str) and v in ALLOWED_ASSOCIATIONS for v in allowed)
    ):
        return f"author_association の許可リスト {allowed} がメンテナー（{sorted(ALLOWED_ASSOCIATIONS)}）以外を含む"
    return None


def check_workflow(rel: str, commands: list[str]) -> list[str]:
    text = (REPO_ROOT / rel).read_text(encoding="utf-8")
    errors = []
    found = False
    for line in text.splitlines():
        match = IF_LINE.match(line)
        if not match or not any(f"'{cmd}'" in match.group(1) for cmd in commands):
            continue
        found = True
        problem = check_condition(match.group(1))
        if problem:
            errors.append(f"{rel}: {problem}: {match.group(1)}")
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
