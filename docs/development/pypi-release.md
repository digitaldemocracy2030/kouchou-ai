# PyPI リリース手順

`kouchou-ai-analysis-core` パッケージを PyPI に公開・更新する手順です。

## 前提条件

- Python 3.12+
- PyPI アカウントと API トークン
- `build` と `twine` がインストール済み

## 1. バージョン更新

`packages/analysis-core/pyproject.toml` のバージョンを更新します：

```toml
[project]
name = "kouchou-ai-analysis-core"
version = "0.1.1"  # ← ここを更新
```

### バージョン番号の規則

- **パッチ (0.1.x)**: バグ修正、ドキュメント更新
- **マイナー (0.x.0)**: 新機能追加（後方互換あり）
- **メジャー (x.0.0)**: 破壊的変更

## 2. 変更のコミット

```bash
git add packages/analysis-core/pyproject.toml
git commit -m "chore: Bump version to 0.1.1"
git tag v0.1.1
git push && git push --tags
```

## 3. ビルド環境の準備

```bash
# 一時ビルド環境を作成（パッケージディレクトリ外で）
cd /tmp
rm -rf pypi-build
mkdir pypi-build && cd pypi-build
python3.12 -m venv venv
venv/bin/pip install build twine
```

## 4. パッケージのビルド

```bash
# 既存の dist を削除
rm -rf /path/to/kouchou-ai/packages/analysis-core/dist

# ビルド実行
venv/bin/python -m build /path/to/kouchou-ai/packages/analysis-core
```

成功すると以下が生成されます：
```
packages/analysis-core/dist/
├── kouchou_ai_analysis_core-0.1.1-py3-none-any.whl
└── kouchou_ai_analysis_core-0.1.1.tar.gz
```

## 5. PyPI へアップロード

### 本番 PyPI

```bash
cd /tmp/pypi-build
venv/bin/twine upload /path/to/kouchou-ai/packages/analysis-core/dist/*
```

プロンプトで認証情報を入力：
- **Username**: `__token__`
- **Password**: PyPI API トークン (`pypi-xxxx...`)

### TestPyPI（テスト用）

```bash
venv/bin/twine upload --repository testpypi /path/to/kouchou-ai/packages/analysis-core/dist/*
```

TestPyPI からのインストール確認：
```bash
pip install --index-url https://test.pypi.org/simple/ kouchou-ai-analysis-core
```

## 6. リリース確認

```bash
# PyPI からインストール
pip install --upgrade kouchou-ai-analysis-core

# バージョン確認
kouchou-analyze --version
```

## 環境変数での認証（CI/CD 用）

```bash
export TWINE_USERNAME=__token__
export TWINE_PASSWORD=pypi-xxxxxxxxxxxxxxxx

twine upload dist/*
```

## .pypirc ファイルでの認証

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

## GitHub Actions での自動リリース（参考）

```yaml
# .github/workflows/publish.yml
name: Publish to PyPI

on:
  push:
    tags:
      - 'v*'

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Build
        run: |
          pip install build
          python -m build packages/analysis-core
      - name: Publish
        uses: pypa/gh-action-pypi-publish@release/v1
        with:
          packages-dir: packages/analysis-core/dist/
          password: ${{ secrets.PYPI_API_TOKEN }}
```

## リリースチェックリスト

- [ ] テストが全てパス (`pytest`)
- [ ] バージョン番号を更新
- [ ] CHANGELOG/リリースノートを更新（必要に応じて）
- [ ] コミット & タグ作成
- [ ] ビルド成功
- [ ] TestPyPI でテスト（オプション）
- [ ] PyPI にアップロード
- [ ] インストール確認

---

**PyPI パッケージページ**: https://pypi.org/project/kouchou-ai-analysis-core/
