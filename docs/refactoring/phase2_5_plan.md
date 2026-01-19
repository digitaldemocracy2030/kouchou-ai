# Phase 2.5: PyPIパッケージ化 詳細計画

## 概要

Phase 2 で作成した `packages/analysis-core/` を、PyPI配布可能な形に整理し、`apps/api` から利用できるようにする。

## 現状

### 完了している項目
- パッケージ構造作成済み (`packages/analysis-core/`)
- 全ステップ移行済み (8ステップ)
- コアユーティリティ移行済み (`core/orchestration.py`, `core/utils.py`)
- サービス移行済み (`services/llm.py`, `services/parse_json_list.py`)
- pyproject.toml 作成済み
- 基本テスト通過 (20 tests)

### 未完了の項目
1. **オーケストレーター実装がスタブ**
   - `orchestrator.py` の `run()` メソッドが未実装
   - `__main__.py` がレガシーへのリダイレクトのみ

2. **apps/api との統合未実施**
   - `report_launcher.py` は依然として `hierarchical_main.py` を subprocess で呼び出し

3. **initialization 関数が未移行**
   - `hierarchical_utils.py` の `initialization()` は `core/orchestration.py` に含まれていない

---

## 実施タスク

### Task 2.5.1: initialization 関数の移行

**目的**: パイプライン初期化ロジックを analysis-core に完全移行

**変更ファイル**:
- `packages/analysis-core/src/analysis_core/core/orchestration.py`

**実装内容**:
```python
def initialization(
    config_path: Path,
    force: bool = False,
    only: str | None = None,
    skip_interaction: bool = False,
    without_html: bool = True,
    output_base_dir: Path | None = None,
    prompts_dir: Path | None = None,
    steps_dir: Path | None = None,
) -> dict[str, Any]:
    """
    Initialize pipeline configuration.

    Args:
        config_path: Path to config JSON file
        force: Force re-run all steps
        only: Run only specified step
        skip_interaction: Skip interactive prompts
        without_html: Skip HTML visualization
        output_base_dir: Base directory for outputs
        prompts_dir: Directory containing prompt files
        steps_dir: Directory containing step source files

    Returns:
        Initialized configuration dictionary
    """
```

**ポイント**:
- ハードコードされた `PIPELINE_DIR` を引数で設定可能に
- プロンプトファイルとソースコードのパスを外部から注入可能に
- `LLMPricing` 依存を optional callback に変更（既に `run_step` で対応済み）

### Task 2.5.2: PipelineOrchestrator の完成

**目的**: スタブ実装を実際に動作するオーケストレーターに変更

**変更ファイル**:
- `packages/analysis-core/src/analysis_core/orchestrator.py`

**実装内容**:
```python
class PipelineOrchestrator:
    def __init__(
        self,
        config: dict[str, Any] | Path,
        output_dir: Path | None = None,
        prompts_dir: Path | None = None,
        steps: list[str] | None = None,
    ):
        """
        Initialize orchestrator.

        Args:
            config: Configuration dict or path to JSON file
            output_dir: Output directory for results
            prompts_dir: Directory containing prompt templates
            steps: List of steps to execute (default: all 8 steps)
        """

    def run(
        self,
        force: bool = False,
        only_step: str | None = None,
        skip_html: bool = True,
        skip_interaction: bool = True,
    ) -> PipelineResult:
        """Execute the pipeline."""
        # 1. Call initialization
        # 2. Execute each step via run_step
        # 3. Call termination
        # 4. Return PipelineResult
```

**ステップ関数の登録**:
```python
# デフォルトステップの自動登録
from analysis_core.steps import (
    extraction, embedding, hierarchical_clustering,
    hierarchical_initial_labelling, hierarchical_merge_labelling,
    hierarchical_overview, hierarchical_aggregation, hierarchical_visualization,
)

DEFAULT_STEP_FUNCTIONS = {
    "extraction": extraction,
    "embedding": embedding,
    "hierarchical_clustering": hierarchical_clustering,
    "hierarchical_initial_labelling": hierarchical_initial_labelling,
    "hierarchical_merge_labelling": hierarchical_merge_labelling,
    "hierarchical_overview": hierarchical_overview,
    "hierarchical_aggregation": hierarchical_aggregation,
    "hierarchical_visualization": hierarchical_visualization,
}
```

### Task 2.5.3: CLI実装の完成

**目的**: `kouchou-analyze` CLI を実際に動作させる

**変更ファイル**:
- `packages/analysis-core/src/analysis_core/__main__.py`

**実装内容**:
```python
def main() -> int:
    parser = argparse.ArgumentParser(...)
    # 既存の引数定義

    args = parser.parse_args()

    # 設定ファイル読み込み
    config = PipelineConfig.from_json(args.config)

    # オーケストレーター作成・実行
    orchestrator = PipelineOrchestrator(
        config=config.to_dict(),
        output_dir=args.output_dir,
    )

    result = orchestrator.run(
        force=args.force,
        only_step=args.only,
        skip_html=args.without_html,
        skip_interaction=args.skip_interaction,
    )

    return 0 if result.success else 1
```

### Task 2.5.4: プロンプトファイルの移行

**目的**: プロンプトテンプレートをパッケージに含める

**変更内容**:
1. `packages/analysis-core/src/analysis_core/prompts/` ディレクトリ作成
2. 各ステップのプロンプトファイルをコピー:
   ```
   prompts/
   ├── extraction/
   │   └── default.txt
   ├── hierarchical_initial_labelling/
   │   └── default.txt
   ├── hierarchical_merge_labelling/
   │   └── default.txt
   └── hierarchical_overview/
       └── default.txt
   ```
3. `pyproject.toml` に package-data 設定追加:
   ```toml
   [tool.hatch.build.targets.wheel]
   packages = ["src/analysis_core"]

   [tool.hatch.build.targets.wheel.sources]
   "src" = ""

   [tool.hatch.build]
   include = [
       "src/analysis_core/**/*.py",
       "src/analysis_core/**/*.json",
       "src/analysis_core/**/*.txt",
   ]
   ```

### Task 2.5.5: apps/api からの呼び出し切り替え

**目的**: report_launcher.py を analysis-core ライブラリ使用に変更

**方針の選択肢**:

| 方式 | メリット | デメリット |
|------|----------|------------|
| A. subprocess維持 (CLIを呼ぶ) | 変更最小、分離度高い | パフォーマンス、エラーハンドリング困難 |
| B. ライブラリ直接呼び出し | 柔軟、エラー伝播容易 | 依存関係複雑化 |
| C. ハイブリッド | 段階移行可能 | 2つの方式を維持 |

**推奨: 方式A（subprocess維持）**

理由:
- 既存の動作を維持しつつ移行
- analysis-core の独立性を保持
- 将来的に方式Bへの移行も可能

**変更ファイル**:
- `apps/api/src/services/report_launcher.py`

**変更内容**:
```python
# Before:
cmd = ["python", "hierarchical_main.py", config_path, "--skip-interaction", "--without-html"]
execution_dir = settings.TOOL_DIR / "pipeline"

# After:
cmd = ["python", "-m", "analysis_core", "--config", str(config_path), "--skip-interaction", "--without-html"]
# または
cmd = ["kouchou-analyze", "--config", str(config_path), "--skip-interaction", "--without-html"]
```

**apps/api への依存追加**:
```toml
# apps/api/pyproject.toml
dependencies = [
    # 既存依存関係
    "kouchou-ai-analysis-core",  # 追加
]
```

### Task 2.5.6: 依存関係の整理

**目的**: 依存ライブラリを軽量化し、オプション依存を分離

**現在の依存関係** (`pyproject.toml`):
```toml
dependencies = [
    "pandas>=2.2.3",
    "numpy>=1.26.0",
    "openai>=1.77.0",
    "sentence-transformers>=2.7.0",  # 重い
    "scikit-learn>=1.5.0",
    "scipy>=1.15.1",
    "umap-learn>=0.5.7",
    "tqdm>=4.66.0",
    "pydantic>=2.0.0",
    "tenacity>=9.1.2",
    "python-dotenv>=1.0.1",
]
```

**変更後**:
```toml
dependencies = [
    # Core (必須)
    "pandas>=2.2.3",
    "numpy>=1.26.0",
    "pydantic>=2.0.0",
    "tqdm>=4.66.0",
    "python-dotenv>=1.0.1",
    "tenacity>=9.1.2",
]

[project.optional-dependencies]
# LLM providers
openai = ["openai>=1.77.0"]
gemini = ["google-generativeai>=0.8.4"]

# Embeddings (local)
embeddings = [
    "sentence-transformers>=2.7.0",
    "torch>=2.0.0",
]

# Clustering
clustering = [
    "scikit-learn>=1.5.0",
    "scipy>=1.15.1",
    "umap-learn>=0.5.7",
]

# Full installation (all features)
full = [
    "kouchou-ai-analysis-core[openai,embeddings,clustering]",
]

# Development
dev = [
    "pytest>=8.0.0",
    "pytest-cov>=4.0.0",
    "ruff>=0.4.0",
]
```

**Note**: この分離は将来の検討事項。現時点では全依存を維持し、動作を確認する。

### Task 2.5.7: テストの拡充

**目的**: 統合テストとCLIテストを追加

**新規テストファイル**:
1. `tests/test_orchestrator.py` - オーケストレーター単体テスト
2. `tests/test_cli.py` - CLIテスト
3. `tests/test_integration.py` - エンドツーエンドテスト（モック使用）

**test_orchestrator.py の例**:
```python
import pytest
from analysis_core import PipelineOrchestrator, PipelineConfig

class TestPipelineOrchestrator:
    def test_init_with_dict(self):
        config = {"input": "test", "question": "Test?"}
        orchestrator = PipelineOrchestrator(config)
        assert orchestrator.config == config

    def test_init_with_path(self, tmp_path):
        config_path = tmp_path / "config.json"
        config_path.write_text('{"input": "test", "question": "Test?"}')
        orchestrator = PipelineOrchestrator(config_path)
        assert orchestrator.config["input"] == "test"

    def test_step_registration(self):
        orchestrator = PipelineOrchestrator({"input": "test", "question": "?"})
        def dummy_step(config): pass
        orchestrator.register_step("custom", dummy_step)
        assert "custom" in orchestrator._step_functions
```

### Task 2.5.8: バージョニングとリリース準備

**目的**: バージョン管理とリリースワークフローを整備

**バージョニング戦略**:
- Semantic Versioning (SemVer) を採用
- 初期バージョン: 0.1.0 (Alpha)
- `__init__.py` で `__version__` を定義（既存）

**リリースワークフロー** (将来の GitHub Actions):
```yaml
# .github/workflows/publish-analysis-core.yml
name: Publish analysis-core to PyPI

on:
  push:
    tags:
      - 'analysis-core-v*'

jobs:
  publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - name: Build package
        run: |
          cd packages/analysis-core
          pip install build
          python -m build
      - name: Publish to PyPI
        uses: pypa/gh-action-pypi-publish@release/v1
        with:
          packages-dir: packages/analysis-core/dist/
```

---

## 実施順序

```
Task 2.5.1: initialization 関数の移行
    ↓
Task 2.5.4: プロンプトファイルの移行
    ↓
Task 2.5.2: PipelineOrchestrator の完成
    ↓
Task 2.5.3: CLI実装の完成
    ↓
Task 2.5.7: テストの拡充
    ↓
Task 2.5.5: apps/api からの呼び出し切り替え
    ↓
Task 2.5.6: 依存関係の整理（オプション）
    ↓
Task 2.5.8: バージョニングとリリース準備
```

---

## 検証基準

### 必須
- [ ] `packages/analysis-core` のテストが全て通過
- [ ] CLI (`kouchou-analyze --config test.json`) が動作
- [ ] `apps/api` から analysis-core 経由でパイプライン実行可能
- [ ] 既存の `make test/api` が通過

### 推奨
- [ ] サンプルデータでエンドツーエンド実行
- [ ] 出力JSONが既存フォーマットと互換

---

## リスクと対策

| リスク | 対策 |
|--------|------|
| パス解決の問題 | 相対パスを避け、設定で明示的に指定 |
| 依存関係の衝突 | apps/api と同じ依存バージョンを維持 |
| プロンプトファイル欠損 | package_data で確実にバンドル |
| 既存APIの回帰 | 既存テスト維持 + 統合テスト追加 |

---

## 見積もり工数

| タスク | 想定時間 |
|--------|----------|
| 2.5.1 initialization移行 | 1-2時間 |
| 2.5.2 Orchestrator完成 | 2-3時間 |
| 2.5.3 CLI完成 | 1時間 |
| 2.5.4 プロンプト移行 | 30分 |
| 2.5.5 apps/api統合 | 1-2時間 |
| 2.5.6 依存整理 | 1時間（オプション） |
| 2.5.7 テスト拡充 | 2-3時間 |
| 2.5.8 リリース準備 | 1時間 |
| **合計** | **9-13時間** |
