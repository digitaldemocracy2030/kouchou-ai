# PyPI リリース手順

`kouchou-ai-analysis-core` パッケージを PyPI に公開・更新する手順です。

## 公開の仕組み

`analysis-core-v*` の形のタグ（例: `analysis-core-v0.1.4`）を GitHub に push すると、`.github/workflows/publish-analysis-core.yml` が起動します。このワークフローは Ruff と pytest を実行し、パッケージをビルドしたうえで、**本番 PyPI に自動で公開します**。

- タグを push した時点で公開が始まります。手元でのビルド確認や TestPyPI での確認は、すべて**タグを push する前**に済ませてください
- GitHub の Actions 画面からワークフローを手動実行（workflow_dispatch）した場合も、選んだブランチの内容で本番 PyPI に公開されます
- 公開されるバージョン番号は、タグ名ではなく `pyproject.toml` の `version` です。ワークフローはタグ名と `version` が一致するかを確かめないので、タグを付けるコミットで両者が一致していることを確認してください
- 公開済みのバージョンは、同じ番号で上書き・再アップロードできません。やり直す場合はバージョン番号を上げます
- 公開の手順は、このリポジトリ（`digitaldemocracy2030/kouchou-ai`）でだけ実行されます。fork では公開せずに終わります

## 前提条件

- Python 3.12+
- 手元でビルドを確かめるための `build`（TestPyPI を使う場合は `twine` と TestPyPI の API トークンも）
- このリポジトリにタグを push できる権限（本番 PyPI への公開は、GitHub Actions がリポジトリの secret `PYPI_API_TOKEN` を使って行います）

## 1. バージョン更新

バージョン番号は 2 か所にあります。**両方を同じ番号に更新してください**。

`packages/analysis-core/pyproject.toml`（公開されるパッケージのバージョン）：

```toml
[project]
name = "kouchou-ai-analysis-core"
version = "0.1.4"  # ← ここを更新
```

`packages/analysis-core/src/analysis_core/__init__.py`（`kouchou-analyze --version` や `analysis_core.__version__` が表示するバージョン）：

```python
__version__ = "0.1.4"  # ← ここも更新
```

片方だけを更新すると、`tests/test_version.py` が失敗します（自動公開の前に実行される pytest でも止まります）。

### バージョン番号の規則

- **パッチ (0.1.x)**: バグ修正、ドキュメント更新
- **マイナー (0.x.0)**: 新機能追加（後方互換あり）
- **メジャー (x.0.0)**: 破壊的変更

## 2. テストと手元でのビルド確認

タグを push する前に、手元でテストとビルドを確かめます。

```bash
cd /path/to/kouchou-ai/packages/analysis-core
pytest
```

```bash
# 一時ビルド環境を作成（パッケージディレクトリ外で）
cd /tmp
rm -rf pypi-build
mkdir pypi-build && cd pypi-build
python3.12 -m venv venv
venv/bin/pip install build twine

# 既存の dist を削除
rm -rf /path/to/kouchou-ai/packages/analysis-core/dist

# ビルド実行
venv/bin/python -m build /path/to/kouchou-ai/packages/analysis-core
```

成功すると以下が生成されます：
```
packages/analysis-core/dist/
├── kouchou_ai_analysis_core-0.1.4-py3-none-any.whl
└── kouchou_ai_analysis_core-0.1.4.tar.gz
```

## 3. TestPyPI での確認（任意）

本番に公開する前に、TestPyPI で確かめることができます。TestPyPI へのアップロードは自動では行われないので、手元から行います。

```bash
cd /tmp/pypi-build
venv/bin/twine upload --repository testpypi /path/to/kouchou-ai/packages/analysis-core/dist/*
```

プロンプトで認証情報を入力：
- **Username**: `__token__`
- **Password**: TestPyPI の API トークン

TestPyPI からのインストール確認（依存パッケージは本番 PyPI から取得します）：
```bash
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ kouchou-ai-analysis-core==0.1.4
kouchou-analyze --version
```

TestPyPI でも、同じバージョン番号は再アップロードできません。

## 4. 変更のコミットとマージ

バージョン更新をコミットし、PR を作って main にマージします。

```bash
git add packages/analysis-core/pyproject.toml packages/analysis-core/src/analysis_core/__init__.py
git commit -m "chore(analysis-core): バージョンを 0.1.4 に上げる"
```

## 5. タグの push（本番 PyPI への自動公開）

main にマージされたら、マージ後のコミットにタグを付けて push します。**push した時点で本番 PyPI への公開が始まります**。

```bash
git checkout main
git pull
git tag analysis-core-v0.1.4
git push origin analysis-core-v0.1.4
```

`git push --tags` は手元にある他のタグもまとめて push してしまうため、公開するタグだけを指定してください。

push 後、GitHub の Actions 画面で「Publish analysis-core to PyPI」が成功したことを確認します。テストやビルドで失敗した場合は公開されません。原因を直したうえで、バージョン番号を上げてやり直してください（同じ番号を使い直す場合は、push 済みのタグを削除してから付け直します）。

## 6. リリース確認

```bash
# PyPI からインストール
pip install --upgrade kouchou-ai-analysis-core

# バージョン確認（新しい番号が表示されること）
kouchou-analyze --version
```

## 手動でアップロードする場合（自動公開が使えないとき）

GitHub Actions が使えないなど、自動公開ができない場合だけ、手元から本番 PyPI にアップロードします。上の 1〜4 を済ませてから、手順 5 のタグの push の代わりに次を実行します。

```bash
cd /tmp/pypi-build
venv/bin/twine upload /path/to/kouchou-ai/packages/analysis-core/dist/*
```

プロンプトで認証情報を入力：
- **Username**: `__token__`
- **Password**: PyPI API トークン (`pypi-xxxx...`)

タグを push すると自動公開が動くため、すでに手動で公開したバージョンのタグを後から push すると、ワークフローが同じバージョンを公開しようとして失敗します。逆に、タグを push して自動公開した後に同じバージョンを手動でアップロードすると、`File already exists` で失敗します。

### 環境変数での認証

```bash
export TWINE_USERNAME=__token__
export TWINE_PASSWORD=pypi-xxxxxxxxxxxxxxxx

twine upload dist/*
```

### .pypirc ファイルでの認証

```ini
# ~/.pypirc
[pypi]
username = __token__
password = pypi-xxxxxxxxxxxxxxxx

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = pypi-xxxxxxxxxxxxxxxx
```

```bash
chmod 600 ~/.pypirc
```

## トラブルシューティング

### `HTTPError: 400 Bad Request - File already exists`

同じバージョンは再アップロードできません。バージョン番号を上げてください。

### `AbsoluteLinkError` (symlink エラー)

パッケージディレクトリ内に venv がある場合に発生します。
ビルドは必ず**パッケージディレクトリの外**で行ってください。

### ビルドエラー: `project.urls` の構文

`[project.urls]` セクションは `classifiers` や `dependencies` の**後**に配置してください：

```toml
[project]
name = "..."
classifiers = [...]
dependencies = [...]

[project.optional-dependencies]
...

[project.urls]  # ← ここ
Homepage = "..."

[project.scripts]
...
```

## GitHub Actions のワークフロー

自動公開の定義は [`.github/workflows/publish-analysis-core.yml`](https://github.com/digitaldemocracy2030/kouchou-ai/blob/main/.github/workflows/publish-analysis-core.yml) にあります。起動の条件（タグの push と手動実行）、公開前に実行するチェック（Ruff・pytest）、公開先の設定は、このファイルを直接確認してください。

## リリースチェックリスト

- [ ] `pyproject.toml` の `version` と `__init__.py` の `__version__` を同じ番号に更新
- [ ] テストが全てパス (`pytest`)
- [ ] CHANGELOG/リリースノートを更新（必要に応じて）
- [ ] 手元でのビルド成功
- [ ] wheel / sdist のライセンス表記がAGPL-3.0で、rootの `LICENSE` と同じ全文が同梱されている
- [ ] TestPyPI でテスト（オプション）
- [ ] 上記確認後に PR をマージし、`analysis-core-vX.Y.Z` タグを push（タグpushで自動公開が始まる）
- [ ] GitHub Actions の公開ワークフローが成功
- [ ] インストール確認（`kouchou-analyze --version` が新しい番号）

---

**PyPI パッケージページ**: https://pypi.org/project/kouchou-ai-analysis-core/
