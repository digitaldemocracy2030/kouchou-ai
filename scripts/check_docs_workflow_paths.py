"""docs.yml の paths が、docs_hooks.py で docs に複製するファイルを漏れなく含むかを確認する。

使い方: python scripts/check_docs_workflow_paths.py

docs_hooks.py の FILE_MAPPINGS に README などを追加した時は、
.github/workflows/docs.yml の push / pull_request の paths にも同じパスを追加すること。
paths に漏れがあると、そのファイルだけを変えた PR ではドキュメントのビルド（--strict）が走らず、
main にマージしても公開サイトが更新されない。
"""

import importlib.util
import re
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "docs.yml"
HOOKS = REPO_ROOT / "scripts" / "docs_hooks.py"


def load_file_mappings() -> dict[str, str]:
    spec = importlib.util.spec_from_file_location("docs_hooks", HOOKS)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.FILE_MAPPINGS


def glob_to_regex(pattern: str) -> re.Pattern[str]:
    """GitHub Actions の paths フィルタ（*, ** のみ）を正規表現にする。"""
    out = ""
    i = 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out += "(?:.*/)?"
            i += 3
        elif pattern.startswith("**", i):
            out += ".*"
            i += 2
        elif pattern[i] == "*":
            out += "[^/]*"
            i += 1
        else:
            out += re.escape(pattern[i])
            i += 1
    return re.compile(out + r"\Z")


def is_glob(pattern: str) -> bool:
    return any(ch in pattern for ch in "*?[")


def main() -> int:
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    # PyYAML は "on" を真偽値 True として読む
    triggers = workflow.get("on", workflow.get(True))
    sources = sorted(load_file_mappings())
    errors: list[str] = []

    for event in ("push", "pull_request"):
        paths = triggers[event]["paths"]
        regexes = [glob_to_regex(p) for p in paths]
        for source in sources:
            if not any(r.match(source) for r in regexes):
                errors.append(
                    f"{event}.paths に {source} がありません（docs_hooks.py の FILE_MAPPINGS で複製しています）"
                )
        for path in paths:
            if not is_glob(path) and not (REPO_ROOT / path).exists():
                errors.append(f"{event}.paths の {path} は存在しません")

    if errors:
        print(
            f"{WORKFLOW.relative_to(REPO_ROOT)} の paths が docs_hooks.py とずれています:",
            file=sys.stderr,
        )
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        return 1
    print(
        f"OK: {len(sources)} 件の複製元が push / pull_request の paths に含まれています"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
