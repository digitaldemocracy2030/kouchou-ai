# Phase 3: 分析プラグイン化 詳細計画

## 概要

既存の8つのパイプラインステップをプラグインアーキテクチャに変換し、ワークフロー定義で手順を制御できるようにする。

## 前提条件

Phase 2.5 が完了していること:
- `analysis-core` パッケージが動作する状態
- CLI とライブラリAPIが利用可能
- `apps/api` から `analysis-core` 経由でパイプライン実行可能

---

## 現状分析

### 現在のステップ構造

```python
# 現在のステップ関数シグネチャ
def extraction(config: dict[str, Any]) -> None:
    """
    - config から設定を取得
    - ファイルパスはハードコード（outputs/{dataset}/...）
    - 結果は直接ファイルに書き込み
    """
```

### 現在の specs.json 構造

```json
{
    "step": "extraction",
    "filename": "args.csv",
    "dependencies": {"params": ["limit"], "steps": []},
    "options": {"limit": 1000, "workers": 1, ...},
    "use_llm": true
}
```

### 問題点

1. **ステップ関数が config 全体に依存** - 疎結合でない
2. **ファイルパスがハードコード** - `outputs/{dataset}/` 固定
3. **ステップ順序が hierarchical_main.py にハードコード** - 拡張性なし
4. **プラグインの動的読み込み機構がない**
5. **ワークフロー定義の概念がない**

---

## 目標アーキテクチャ

### プラグインマニフェスト

```yaml
# plugins/analysis/extraction/manifest.yaml
id: analysis.extraction
version: "1.0.0"
kind: analysis-step
name: "Extraction"
description: "コメントから意見を抽出"

entry: extraction:run  # モジュール:関数

config_schema:
  type: object
  properties:
    limit:
      type: integer
      default: 1000
    workers:
      type: integer
      default: 1
    prompt:
      type: string
      required: true
    model:
      type: string
      default: "gpt-4o-mini"

inputs:
  - id: comments
    type: csv
    required: true

outputs:
  - id: arguments
    type: csv
    filename: args.csv
  - id: relations
    type: csv
    filename: relations.csv

dependencies:
  steps: []
  params: [limit]

use_llm: true
```

### ステップインターフェース

```python
# analysis_core/plugin/interface.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Any

@dataclass
class StepContext:
    """ステップ実行コンテキスト"""
    output_dir: Path
    input_dir: Path
    dataset: str
    provider: str
    model: str
    local_llm_address: str | None = None
    user_api_key: str | None = None

@dataclass
class StepInputs:
    """ステップへの入力"""
    artifacts: dict[str, Path]  # artifact_id -> file_path

@dataclass
class StepOutputs:
    """ステップの出力"""
    artifacts: dict[str, Path]  # artifact_id -> file_path
    token_usage: int = 0
    token_input: int = 0
    token_output: int = 0

class AnalysisStepPlugin(ABC):
    """分析ステッププラグインの基底クラス"""

    @property
    @abstractmethod
    def id(self) -> str:
        """プラグインID"""
        pass

    @property
    @abstractmethod
    def version(self) -> str:
        """バージョン"""
        pass

    @abstractmethod
    def run(
        self,
        ctx: StepContext,
        inputs: StepInputs,
        config: dict[str, Any],
    ) -> StepOutputs:
        """ステップを実行"""
        pass

    def validate_config(self, config: dict[str, Any]) -> list[str]:
        """設定を検証（エラーメッセージのリストを返す）"""
        return []
```

### 関数ベースのプラグイン（簡易版）

```python
# より軽量な関数ベースのプラグイン定義
from analysis_core.plugin import step_plugin

@step_plugin(
    id="analysis.extraction",
    version="1.0.0",
    inputs=["comments"],
    outputs=["arguments", "relations"],
    use_llm=True,
)
def extraction(
    ctx: StepContext,
    inputs: StepInputs,
    config: dict[str, Any],
) -> StepOutputs:
    """意見抽出ステップ"""
    ...
```

### ワークフロー定義

```yaml
# workflows/hierarchical-default.yaml
id: hierarchical-default
version: "1.0.0"
name: "階層クラスタリング（デフォルト）"
description: "標準的な階層クラスタリング分析ワークフロー"

steps:
  - id: extraction
    plugin: analysis.extraction
    config:
      limit: ${config.extraction.limit}
      workers: ${config.extraction.workers}
      prompt: ${config.extraction.prompt}
      model: ${config.model}

  - id: embedding
    plugin: analysis.embedding
    depends_on: [extraction]
    config:
      model: ${config.embedding.model}

  - id: clustering
    plugin: analysis.hierarchical_clustering
    depends_on: [embedding]
    config:
      cluster_nums: ${config.hierarchical_clustering.cluster_nums}

  - id: initial_labelling
    plugin: analysis.hierarchical_initial_labelling
    depends_on: [clustering]
    config:
      sampling_num: ${config.hierarchical_initial_labelling.sampling_num}
      prompt: ${config.hierarchical_initial_labelling.prompt}
      model: ${config.model}

  - id: merge_labelling
    plugin: analysis.hierarchical_merge_labelling
    depends_on: [initial_labelling]
    config:
      sampling_num: ${config.hierarchical_merge_labelling.sampling_num}
      prompt: ${config.hierarchical_merge_labelling.prompt}
      model: ${config.model}

  - id: overview
    plugin: analysis.hierarchical_overview
    depends_on: [merge_labelling]
    config:
      prompt: ${config.hierarchical_overview.prompt}
      model: ${config.model}

  - id: aggregation
    plugin: analysis.hierarchical_aggregation
    depends_on: [extraction, clustering, initial_labelling, merge_labelling, overview]

  - id: visualization
    plugin: analysis.hierarchical_visualization
    depends_on: [aggregation]
    optional: true
    condition: ${not config.without_html}
```

---

## 実施タスク

### Task 3.1: プラグインインターフェース定義

**目的**: ステッププラグインの基盤となるインターフェースを定義

**新規ファイル**:
```
packages/analysis-core/src/analysis_core/
├── plugin/
│   ├── __init__.py
│   ├── interface.py      # StepContext, StepInputs, StepOutputs, AnalysisStepPlugin
│   ├── registry.py       # プラグインレジストリ
│   ├── loader.py         # プラグイン読み込み
│   └── decorator.py      # @step_plugin デコレータ
```

**実装内容**:
1. `StepContext`, `StepInputs`, `StepOutputs` データクラス
2. `AnalysisStepPlugin` 抽象基底クラス
3. `@step_plugin` デコレータ（関数ベースプラグイン用）

### Task 3.2: プラグインレジストリ実装

**目的**: プラグインの登録・検索・管理

**実装内容**:
```python
# analysis_core/plugin/registry.py
class PluginRegistry:
    """プラグインレジストリ"""

    def __init__(self):
        self._plugins: dict[str, AnalysisStepPlugin] = {}
        self._builtin_registered = False

    def register(self, plugin: AnalysisStepPlugin) -> None:
        """プラグインを登録"""
        self._plugins[plugin.id] = plugin

    def get(self, plugin_id: str) -> AnalysisStepPlugin | None:
        """プラグインを取得"""
        return self._plugins.get(plugin_id)

    def list_plugins(self) -> list[str]:
        """登録済みプラグインIDの一覧"""
        return list(self._plugins.keys())

    def register_builtin_plugins(self) -> None:
        """組み込みプラグインを登録"""
        if self._builtin_registered:
            return
        # 既存ステップをプラグインとして登録
        from analysis_core.plugins.builtin import register_all
        register_all(self)
        self._builtin_registered = True

# グローバルレジストリ
_global_registry = PluginRegistry()

def get_registry() -> PluginRegistry:
    return _global_registry
```

### Task 3.3: 既存ステップのプラグイン化

**目的**: 8つの既存ステップを新しいプラグインインターフェースに変換

**変換対象**:
| ステップ | プラグインID |
|----------|--------------|
| extraction | analysis.extraction |
| embedding | analysis.embedding |
| hierarchical_clustering | analysis.hierarchical_clustering |
| hierarchical_initial_labelling | analysis.hierarchical_initial_labelling |
| hierarchical_merge_labelling | analysis.hierarchical_merge_labelling |
| hierarchical_overview | analysis.hierarchical_overview |
| hierarchical_aggregation | analysis.hierarchical_aggregation |
| hierarchical_visualization | analysis.hierarchical_visualization |

**変換例（extraction）**:

```python
# analysis_core/plugins/builtin/extraction.py
from analysis_core.plugin import step_plugin, StepContext, StepInputs, StepOutputs

@step_plugin(
    id="analysis.extraction",
    version="1.0.0",
    inputs=["comments"],
    outputs=["arguments", "relations"],
    use_llm=True,
)
def extraction(
    ctx: StepContext,
    inputs: StepInputs,
    config: dict[str, Any],
) -> StepOutputs:
    """意見抽出ステップ"""
    # 入力
    comments_path = inputs.artifacts.get("comments") or (ctx.input_dir / f"{ctx.dataset}.csv")

    # 設定
    model = config.get("model", ctx.model)
    prompt = config["prompt"]
    workers = config.get("workers", 1)
    limit = config.get("limit", 1000)

    # 処理（既存ロジックを流用）
    # ...

    # 出力
    args_path = ctx.output_dir / "args.csv"
    relations_path = ctx.output_dir / "relations.csv"

    return StepOutputs(
        artifacts={
            "arguments": args_path,
            "relations": relations_path,
        },
        token_usage=token_total,
        token_input=token_input,
        token_output=token_output,
    )
```

### Task 3.4: ワークフローエンジン実装

**目的**: ワークフロー定義に基づいてステップを実行

**新規ファイル**:
```
packages/analysis-core/src/analysis_core/
├── workflow/
│   ├── __init__.py
│   ├── definition.py     # ワークフロー定義モデル
│   ├── engine.py         # ワークフロー実行エンジン
│   └── resolver.py       # 依存解決・順序決定
```

**実装内容**:
```python
# analysis_core/workflow/engine.py
@dataclass
class WorkflowDefinition:
    id: str
    version: str
    name: str
    steps: list[WorkflowStep]

@dataclass
class WorkflowStep:
    id: str
    plugin: str
    config: dict[str, Any]
    depends_on: list[str] = field(default_factory=list)
    optional: bool = False
    condition: str | None = None

class WorkflowEngine:
    """ワークフロー実行エンジン"""

    def __init__(self, registry: PluginRegistry):
        self.registry = registry

    def run(
        self,
        workflow: WorkflowDefinition,
        config: dict[str, Any],
        ctx: StepContext,
    ) -> WorkflowResult:
        """ワークフローを実行"""
        # 1. 依存グラフを構築
        # 2. 実行順序を決定（トポロジカルソート）
        # 3. 各ステップを順次実行
        # 4. アーティファクトを次のステップに引き継ぎ
```

### Task 3.5: デフォルトワークフロー定義

**目的**: 現在のhierarchical pipelineと同等のワークフローを定義

**新規ファイル**:
```
packages/analysis-core/src/analysis_core/workflows/
├── __init__.py
├── hierarchical_default.py  # Python定義版
└── hierarchical_default.yaml  # YAML定義版（将来）
```

### Task 3.6: 互換レイヤー実装

**目的**: 旧config形式から新ワークフローへの変換

**実装内容**:
```python
# analysis_core/compat/config_converter.py
def convert_legacy_config(
    legacy_config: dict[str, Any],
) -> tuple[WorkflowDefinition, dict[str, Any]]:
    """
    旧形式のconfigを新形式に変換

    Returns:
        (workflow_definition, resolved_config)
    """
    # デフォルトワークフローを使用
    workflow = load_workflow("hierarchical-default")

    # config を新形式に変換
    new_config = {
        "extraction": legacy_config.get("extraction", {}),
        "embedding": legacy_config.get("embedding", {}),
        # ...
    }

    return workflow, new_config
```

### Task 3.7: Orchestrator のワークフロー対応

**目的**: PipelineOrchestrator をワークフローベースに更新

**変更内容**:
```python
class PipelineOrchestrator:
    def __init__(
        self,
        config: dict[str, Any] | Path,
        workflow: str | WorkflowDefinition | None = None,
        registry: PluginRegistry | None = None,
        # ...
    ):
        self.registry = registry or get_registry()
        self.registry.register_builtin_plugins()

        # ワークフロー解決
        if workflow is None:
            # 旧config形式 → デフォルトワークフロー
            self.workflow, self.config = convert_legacy_config(config)
        elif isinstance(workflow, str):
            self.workflow = load_workflow(workflow)
            self.config = config
        else:
            self.workflow = workflow
            self.config = config

    def run(self, ...) -> PipelineResult:
        engine = WorkflowEngine(self.registry)
        return engine.run(self.workflow, self.config, self.ctx)
```

### Task 3.8: 外部プラグイン読み込み機構

**目的**: `plugins/analysis/` ディレクトリからプラグインを読み込む

**実装内容**:
```python
# analysis_core/plugin/loader.py
def load_plugins_from_directory(
    directory: Path,
    registry: PluginRegistry,
) -> list[str]:
    """
    ディレクトリからプラグインを読み込み

    構造:
        plugins/analysis/
        ├── my-custom-step/
        │   ├── manifest.yaml
        │   └── plugin.py
    """
    loaded = []
    for plugin_dir in directory.iterdir():
        if not plugin_dir.is_dir():
            continue
        manifest_path = plugin_dir / "manifest.yaml"
        if not manifest_path.exists():
            continue

        # マニフェスト読み込み
        manifest = load_manifest(manifest_path)

        # Pythonモジュール読み込み
        plugin = load_plugin_module(plugin_dir, manifest)

        # レジストリに登録
        registry.register(plugin)
        loaded.append(manifest["id"])

    return loaded
```

### Task 3.9: Analysis 画面の互換性維持

**目的**: `result.config.plan` と `result.config.<step>.source_code/prompt/model` の互換維持

**対応方針**:
- aggregation ステップで従来形式の config を生成
- source_code はプラグインから取得（`inspect.getsource`）
- plan は WorkflowDefinition から生成

---

## ファイル構造（最終形）

```
packages/analysis-core/src/analysis_core/
├── plugin/
│   ├── __init__.py
│   ├── interface.py
│   ├── registry.py
│   ├── loader.py
│   └── decorator.py
├── plugins/
│   └── builtin/
│       ├── __init__.py
│       ├── extraction.py
│       ├── embedding.py
│       ├── hierarchical_clustering.py
│       ├── hierarchical_initial_labelling.py
│       ├── hierarchical_merge_labelling.py
│       ├── hierarchical_overview.py
│       ├── hierarchical_aggregation.py
│       └── hierarchical_visualization.py
├── workflow/
│   ├── __init__.py
│   ├── definition.py
│   ├── engine.py
│   └── resolver.py
├── workflows/
│   ├── __init__.py
│   └── hierarchical_default.py
├── compat/
│   ├── __init__.py
│   └── config_converter.py
└── ... (既存ファイル)
```

---

## 実施順序

```
Task 3.1: プラグインインターフェース定義
    ↓
Task 3.2: プラグインレジストリ実装
    ↓
Task 3.3: 既存ステップのプラグイン化（8ステップ）
    ↓
Task 3.4: ワークフローエンジン実装
    ↓
Task 3.5: デフォルトワークフロー定義
    ↓
Task 3.6: 互換レイヤー実装
    ↓
Task 3.7: Orchestrator のワークフロー対応
    ↓
Task 3.8: 外部プラグイン読み込み機構
    ↓
Task 3.9: Analysis 画面の互換性維持
```

---

## 検証基準

### 必須
- [ ] 既存の config でパイプラインが動作する（互換レイヤー経由）
- [ ] 全8ステップがプラグインとして登録・実行可能
- [ ] 出力JSON形式が既存と同一
- [ ] `apps/api` からの呼び出しが動作
- [ ] Analysis 画面で plan/prompt/source_code が表示される

### 推奨
- [ ] カスタムプラグインを `plugins/analysis/` に追加して動作
- [ ] 新しいワークフロー定義で実行可能
- [ ] プラグインのバージョン管理が機能

---

## リスクと対策

| リスク | 対策 |
|--------|------|
| 既存ステップの挙動変化 | 互換レイヤーで旧形式を維持、差分テスト |
| パス解決の問題 | StepContext で全パスを明示的に管理 |
| プラグイン読み込みエラー | 組み込みプラグインはフォールバックとして常に利用可能 |
| ワークフロー依存解決の複雑化 | トポロジカルソートの十分なテスト |

---

## 見積もり工数

| タスク | 想定時間 |
|--------|----------|
| 3.1 プラグインインターフェース | 2-3時間 |
| 3.2 プラグインレジストリ | 1-2時間 |
| 3.3 既存ステップのプラグイン化 | 4-6時間（8ステップ） |
| 3.4 ワークフローエンジン | 3-4時間 |
| 3.5 デフォルトワークフロー | 1時間 |
| 3.6 互換レイヤー | 1-2時間 |
| 3.7 Orchestrator対応 | 2-3時間 |
| 3.8 外部プラグイン読み込み | 2-3時間 |
| 3.9 Analysis互換性 | 1-2時間 |
| **合計** | **17-26時間** |

---

## 段階的実施の提案

Phase 3 は規模が大きいため、以下のサブフェーズに分割することを推奨:

### Phase 3a: プラグイン基盤（3.1〜3.3）
- プラグインインターフェース
- レジストリ
- 組み込みプラグイン化

### Phase 3b: ワークフロー基盤（3.4〜3.7）
- ワークフローエンジン
- デフォルトワークフロー
- 互換レイヤー
- Orchestrator対応

### Phase 3c: 拡張機能（3.8〜3.9）
- 外部プラグイン読み込み
- UI互換性
