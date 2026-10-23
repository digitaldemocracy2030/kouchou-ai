#!/bin/sh
# lefthook の pre-push から apps/api で ruff を実行する（引数はそのまま ruff に渡す）。
#
# CI（ruff-check.yml）で落ちる前に push 時に検出するためのフック。開発環境によって
# ruff の入手経路が違うので、次の順に使えるものを探す。
#   1. rye（apps/api の dev-dependencies の ruff）
#   2. PATH 上の ruff（requirements-dev.lock を入れた venv など）
#   3. uvx（requirements-dev.lock と同じ版の ruff）
# どれも無い場合（Docker だけで開発している場合など）は警告して検査を飛ばす。
# その場合も CI の ruff-check で検査される。Docker で検査するには `make lint/api-check` を使う。

if command -v rye >/dev/null 2>&1; then
  exec rye run ruff "$@"
fi

if command -v ruff >/dev/null 2>&1; then
  exec ruff "$@"
fi

if command -v uvx >/dev/null 2>&1; then
  version=$(sed -n 's/^ruff==//p' requirements-dev.lock 2>/dev/null)
  exec uvx "ruff${version:+@$version}" "$@"
fi

echo "lefthook: rye / ruff / uvx が見つからないため、ruff $* を飛ばします。" >&2
echo "  push 後に CI（Ruff Check）で検査されます。push 前に確かめるには make lint/api-check を実行してください。" >&2
exit 0
