# PLAN: LLM APIを使用したE2Eパイプラインテストの実装

## 目的
- 実際のLLM APIを使用してパイプライン全体が正しく動作することを検証
- 出力データが期待される構造を持つことを確認
- コスト管理のため自動実行は避け、手動で簡単に実行できる仕組みを提供

## 現状の課題
1. 現在のテストはLLM呼び出しをモックしている
2. 実際のAPIで動くかどうかは手動でDocker環境を立ち上げて確認するしかないがこれは人間の手動ブラウザ操作が挟まって高コストである、CLIで実行できるべき
3. 出力データの構造検証が不十分

## 設計方針

### 1. テストの分類
```
tests/
├── test_*.py                      # 通常のユニットテスト（pytest実行時に自動実行）
├── test_steps_paths.py            # パス検証テスト（自動実行）
├── test_pipeline_paths_integration.py  # 統合テスト（モック使用、自動実行）
└── e2e/                           # E2Eテスト（手動実行、API使用）
    ├── conftest.py                # pytest設定・フィクスチャ
    ├── test_pipeline_e2e.py       # パイプラインE2Eテスト
    ├── fixtures/                  # テスト用の入力データ
    │   └── small_comments.csv     # 最小限のテスト用コメント（5-10件）
    └── schemas/                   # 出力検証用スキーマ
        ├── args.py                # args.csvの構造定義
        ├── hierarchical_result.py # hierarchical_result.jsonの構造定義
        └── clusters.py            # クラスター関連の構造定義
```

### 2. E2Eテストの実行方法
```bash
# 環境変数でAPI KEYを渡して実行
OPENAI_API_KEY=sk-xxx pytest tests/e2e/ -v

# または .env ファイルを使用
# tests/e2e/.env に OPENAI_API_KEY を設定
pytest tests/e2e/ -v

# 特定のテストのみ実行
pytest tests/e2e/test_pipeline_e2e.py::test_full_pipeline -v
```

### 3. 自動実行を防ぐ仕組み
- `tests/e2e/` ディレクトリは `pyproject.toml` の `testpaths` から除外
- E2Eテストには `@pytest.mark.e2e` マーカーを付与
- API KEYが設定されていない場合はスキップ

```python
# conftest.py
@pytest.fixture
def api_key():
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        pytest.skip("OPENAI_API_KEY not set - skipping E2E test")
    return key
```

### 4. テスト入力データ (fixtures/small_comments.csv)
```csv
comment-id,comment-body
1,AIは社会に大きな影響を与えると思います。特に医療分野での活用が期待されます。
2,環境問題への対策として、再生可能エネルギーの普及が重要です。
3,教育のデジタル化により、地方と都市の教育格差が縮小することを期待しています。
4,高齢化社会において、介護ロボットの開発は急務だと考えます。
5,プライバシー保護と利便性のバランスが今後の課題です。
```

### 5. 出力スキーマ検証 (Pydanticモデル)

```python
# schemas/hierarchical_result.py
from pydantic import BaseModel

class Argument(BaseModel):
    arg_id: str
    argument: str
    x: float
    y: float
    p: float
    cluster_ids: list[str]
    attributes: dict[str, str] | None
    url: str | None

class Cluster(BaseModel):
    level: int
    id: str
    label: str
    takeaway: str
    value: int
    parent: str
    density_rank_percentile: float | None

class HierarchicalResult(BaseModel):
    arguments: list[Argument]
    clusters: list[Cluster]
    comment_num: int
    overview: str
    propertyMap: dict
    translations: dict
    config: dict
```

### 6. E2Eテストの内容

```python
# test_pipeline_e2e.py
@pytest.mark.e2e
class TestPipelineE2E:
    def test_full_pipeline_produces_valid_output(self, api_key, temp_dirs):
        """パイプライン全体を実行し、出力が有効な構造を持つことを検証"""
        # 1. テスト用入力をコピー
        # 2. パイプライン実行
        # 3. 出力ファイルの存在確認
        # 4. Pydanticスキーマで構造検証
        # 5. 基本的な整合性チェック

    def test_extraction_produces_arguments(self, api_key, temp_dirs):
        """extractionステップが引数を正しく抽出することを検証"""

    def test_clustering_produces_hierarchy(self, api_key, temp_dirs):
        """クラスタリングが階層構造を正しく生成することを検証"""

    def test_labelling_produces_descriptions(self, api_key, temp_dirs):
        """ラベリングがクラスターに説明を付与することを検証"""
```

### 7. コスト見積もり
- 入力: 5コメント
- extraction: ~500 tokens/コメント × 5 = 2,500 tokens
- embedding: 5 arguments × ~100 tokens = 500 tokens
- labelling: ~2 clusters × ~500 tokens = 1,000 tokens
- overview: ~500 tokens
- **合計: ~4,500 tokens ≈ $0.01 (gpt-4o-mini使用時)**

## 実装タスク

1. [x] `tests/e2e/` ディレクトリ構造の作成
2. [x] `conftest.py` - API KEY検証、スキップロジック、共通フィクスチャ
3. [x] `fixtures/small_comments.csv` - 最小限のテスト用データ
4. [x] `schemas/` - Pydanticによる出力構造定義
5. [x] `test_pipeline_e2e.py` - E2Eテスト実装
6. [x] `pyproject.toml` 更新 - e2eディレクトリを自動実行から除外
7. [x] READMEまたはドキュメント更新 - E2Eテストの実行方法 → `docs/development/testing.md`

## 成功基準
- `pytest tests/e2e/ -v` でAPI KEYがない場合は全テストスキップ
- API KEYがある場合、パイプラインが完走し出力が検証をパス
- 出力JSONがPydanticスキーマでバリデーション成功
- テスト実行時間: 5分以内（5コメントの場合）
