# テスト手法ガイド

このドキュメントでは、kouchou-ai プロジェクトのテスト手法について説明します。

## テストの種類

### 1. ユニットテスト

各コンポーネントの個別機能をテストします。

```bash
# API (Python)
cd apps/api && rye run pytest tests/

# analysis-core パッケージ
cd packages/analysis-core && rye run pytest tests/

# フロントエンド (TypeScript)
cd apps/public-viewer && pnpm test
cd apps/admin && pnpm test
```

### 2. 統合テスト (Integration Tests)

複数のコンポーネントが連携して正しく動作することを検証します。

```bash
# analysis-core の統合テスト
cd packages/analysis-core && rye run pytest tests/test_pipeline_paths_integration.py -v
```

### 3. E2Eテスト (End-to-End Tests)

#### ブラウザE2Eテスト

Playwrightを使用したブラウザ操作のテストです。

```bash
cd test/e2e && pnpm test
cd test/e2e && pnpm run test:ui  # UIモードで実行
```

詳細は [test/e2e/CLAUDE.md](https://github.com/digitaldemocracy2030/kouchou-ai/blob/main/test/e2e/CLAUDE.md) を参照してください。

#### パイプラインE2Eテスト（LLM API使用）

**実際のLLM APIを使用して分析パイプライン全体をテストします。**

このテストは：
- 実際のOpenAI APIを呼び出す
- パイプライン全体（extraction → embedding → clustering → labelling → overview → aggregation）を実行
- 出力データの構造をPydanticスキーマで検証
- コスト: 約$0.01/回（gpt-4o-mini使用、5コメント）

##### 実行方法

```bash
cd packages/analysis-core

# API KEYがない場合は全テストがスキップされる
rye run pytest tests/e2e/ -v

# API KEYを設定して実行
OPENAI_API_KEY=sk-xxx rye run pytest tests/e2e/ -v

# 特定のテストのみ実行
OPENAI_API_KEY=sk-xxx rye run pytest tests/e2e/test_pipeline_e2e.py::TestPipelineE2E::test_full_pipeline_produces_valid_output -v
```

##### 自動実行からの除外

E2Eテストはコストがかかるため、通常の `pytest tests/` 実行時には自動的に除外されます：

```bash
# 通常のテスト実行（e2eは含まれない）
rye run pytest tests/ -v
# 結果: 105 passed（e2eテストは除外）

# e2eを明示的に指定した場合のみ実行
rye run pytest tests/e2e/ -v
```

この除外設定は `pyproject.toml` で行われています：

```toml
[tool.pytest.ini_options]
norecursedirs = ["tests/e2e"]
```

##### テストファイル構成

```
packages/analysis-core/tests/e2e/
├── __init__.py
├── conftest.py           # API KEY検証、フィクスチャ定義
├── test_pipeline_e2e.py  # E2Eテスト本体
├── fixtures/
│   └── small_comments.csv  # テスト用入力（5コメント）
└── schemas/
    ├── __init__.py
    └── hierarchical_result.py  # 出力検証用Pydanticスキーマ
```

##### テスト内容

| テスト名 | 内容 |
|---------|------|
| `test_full_pipeline_produces_valid_output` | 全パイプライン実行、出力ファイル存在確認、スキーマ検証 |
| `test_extraction_produces_arguments` | extractionステップが正しくargs.csvを生成 |
| `test_clustering_produces_hierarchy` | クラスタリングが正しい階層構造を生成 |
| `test_hierarchical_result_schema` | hierarchical_result.jsonのスキーマ準拠を検証 |
| `test_args_csv_schema` | args.csvのスキーマ準拠を検証 |

##### 新しいE2Eテストの追加

新しいテストを追加する場合は、`@pytest.mark.e2e` マーカーを付与してください：

```python
@pytest.mark.e2e
class TestMyNewFeature:
    def test_something(self, api_key, temp_dirs, pipeline_config):
        """新機能のテスト"""
        # api_key フィクスチャを使用すると、
        # OPENAI_API_KEYが未設定の場合は自動的にスキップされる
        ...
```

## CI/CD でのテスト実行

GitHub Actions で自動実行されるテスト：

| ワークフロー | テスト内容 |
|------------|----------|
| `server-pytest.yml` | API サーバーの pytest |
| `client-jest.yml` | public-viewer の Jest |
| `client-admin-jest.yml` | admin の Jest |
| `e2e-tests.yml` | ブラウザ E2E (Playwright) |
| `ruff-check.yml` | Python lint |

**注意**: パイプラインE2Eテスト（LLM API使用）はCIでは実行されません。ローカルで手動実行してください。

## テスト実行のベストプラクティス

1. **コミット前にローカルでテスト実行**
   ```bash
   # 全ユニットテスト
   cd packages/analysis-core && rye run pytest tests/
   cd apps/api && rye run pytest tests/
   ```

2. **重要な変更後はE2Eテストを実行**
   ```bash
   # パイプラインの変更後
   OPENAI_API_KEY=sk-xxx rye run pytest tests/e2e/ -v
   ```

3. **テストカバレッジの確認**
   ```bash
   rye run pytest --cov=analysis_core tests/
   ```
