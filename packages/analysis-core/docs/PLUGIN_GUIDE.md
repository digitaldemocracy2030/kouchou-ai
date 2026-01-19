# プラグイン開発ガイド

analysis-core のプラグインシステムを使用して、カスタム分析ステップを追加する方法を説明します。

## 概要

analysis-core は、分析パイプラインの各ステップをプラグインとして実装するアーキテクチャを採用しています。これにより：

- コアコードを変更せずに新しい分析ステップを追加できる
- 既存のステップを置き換えたり拡張したりできる
- ワークフロー定義で柔軟にステップを組み合わせられる

## プラグインの種類

### 1. 組み込みプラグイン

`analysis_core.plugins.builtin` に含まれる標準プラグイン：

| プラグインID | 説明 |
|-------------|------|
| `analysis.extraction` | コメントから意見を抽出 |
| `analysis.embedding` | 埋め込みベクトル生成 |
| `analysis.hierarchical_clustering` | 階層クラスタリング |
| `analysis.hierarchical_initial_labelling` | 初期ラベリング |
| `analysis.hierarchical_merge_labelling` | 統合ラベリング |
| `analysis.hierarchical_overview` | 概要生成 |
| `analysis.hierarchical_aggregation` | 結果集約 |
| `analysis.hierarchical_visualization` | 可視化HTML生成 |

### 2. 外部プラグイン

`plugins/analysis/` ディレクトリに配置するカスタムプラグイン。

## クイックスタート：関数ベースプラグイン

最も簡単なプラグイン作成方法は `@step_plugin` デコレータを使用することです。

```python
from analysis_core.plugin import (
    step_plugin,
    StepContext,
    StepInputs,
    StepOutputs,
)

@step_plugin(
    id="mycompany.custom_analysis",
    version="1.0.0",
    name="Custom Analysis",
    description="カスタム分析ステップ",
    inputs=["arguments"],  # 依存するアーティファクト
    outputs=["custom_result"],  # 生成するアーティファクト
    use_llm=False,  # LLMを使用するかどうか
)
def custom_analysis_plugin(
    ctx: StepContext,
    inputs: StepInputs,
    config: dict,
) -> StepOutputs:
    """カスタム分析を実行"""

    # 入力ファイルを読み込み
    args_path = inputs.artifacts.get("arguments")

    # 処理を実行
    # ...

    # 結果を保存
    output_path = ctx.output_dir / "custom_result.csv"
    # result_df.to_csv(output_path, index=False)

    return StepOutputs(
        artifacts={"custom_result": output_path},
        token_usage=0,
    )
```

## プラグインインターフェース

### StepContext

ステップ実行時のコンテキスト情報：

```python
@dataclass
class StepContext:
    output_dir: Path      # 出力ディレクトリ
    input_dir: Path       # 入力ディレクトリ
    dataset: str          # データセット名
    provider: str         # LLMプロバイダー (openai, azure, etc.)
    model: str            # LLMモデル名
    local_llm_address: str | None  # ローカルLLMアドレス
    user_api_key: str | None       # ユーザーAPIキー
```

### StepInputs

ステップへの入力：

```python
@dataclass
class StepInputs:
    artifacts: dict[str, Path]  # アーティファクトID → ファイルパス
    config: dict[str, Any]      # 追加の設定
```

### StepOutputs

ステップからの出力：

```python
@dataclass
class StepOutputs:
    artifacts: dict[str, Path]  # 生成したアーティファクト
    token_usage: int = 0        # 使用したトークン数
    token_input: int = 0        # 入力トークン数
    token_output: int = 0       # 出力トークン数
    metadata: dict[str, Any]    # 追加のメタデータ
```

## 外部プラグインの作成

### ディレクトリ構造

```
plugins/analysis/
└── my-custom-step/
    ├── manifest.yaml    # プラグインメタデータ
    └── plugin.py        # プラグイン実装
```

### manifest.yaml

```yaml
id: mycompany.custom_step
version: "1.0.0"
name: "My Custom Step"
description: "カスタム分析ステップの説明"
entry: plugin:custom_step_plugin  # モジュール:属性名

inputs:
  - arguments
  - clusters

outputs:
  - custom_result

use_llm: false

# オプション: 設定スキーマ
config_schema:
  type: object
  properties:
    threshold:
      type: number
      default: 0.5
```

### plugin.py

```python
from analysis_core.plugin import (
    step_plugin,
    StepContext,
    StepInputs,
    StepOutputs,
)

@step_plugin(
    id="mycompany.custom_step",
    version="1.0.0",
    name="My Custom Step",
    description="カスタム分析ステップ",
    inputs=["arguments", "clusters"],
    outputs=["custom_result"],
)
def custom_step_plugin(
    ctx: StepContext,
    inputs: StepInputs,
    config: dict,
) -> StepOutputs:
    # 設定を取得
    threshold = config.get("threshold", 0.5)

    # 入力を読み込み
    args_path = inputs.artifacts.get("arguments")
    clusters_path = inputs.artifacts.get("clusters")

    # 処理...

    # 出力
    output_path = ctx.output_dir / "custom_result.json"
    return StepOutputs(artifacts={"custom_result": output_path})
```

## プラグインの登録と使用

### 手動登録

```python
from analysis_core.plugin import get_registry

# グローバルレジストリを取得
registry = get_registry()

# 組み込みプラグインを登録
registry.register_builtin_plugins()

# カスタムプラグインを登録
registry.register(custom_step_plugin)

# プラグインを取得
plugin = registry.get("mycompany.custom_step")
```

### ディレクトリから読み込み

```python
from pathlib import Path
from analysis_core.plugin import (
    load_plugins_from_directory,
    get_registry,
)

# プラグインディレクトリから読み込み
plugins_dir = Path("plugins/analysis")
loaded = load_plugins_from_directory(plugins_dir, get_registry())

print(f"Loaded {len(loaded)} plugins")
for p in loaded:
    print(f"  - {p.manifest.id} v{p.manifest.version}")
```

### 環境変数で指定

```bash
# プラグインディレクトリを環境変数で指定
export ANALYSIS_PLUGINS_PATH=/path/to/plugins:/another/path

# パイプライン実行時に自動的に読み込まれる
python -m analysis_core config.json
```

## ワークフローでの使用

カスタムプラグインをワークフローで使用するには：

```python
from analysis_core.workflow import WorkflowDefinition, WorkflowStep

workflow = WorkflowDefinition(
    id="custom-workflow",
    version="1.0.0",
    name="Custom Analysis Workflow",
    steps=[
        WorkflowStep(
            id="extract",
            plugin="analysis.extraction",
        ),
        WorkflowStep(
            id="embed",
            plugin="analysis.embedding",
            depends_on=["extract"],
        ),
        WorkflowStep(
            id="custom",
            plugin="mycompany.custom_step",  # カスタムプラグイン
            depends_on=["extract"],
            config={"threshold": 0.7},
        ),
    ],
)
```

## LLMを使用するプラグイン

LLMを使用するプラグインの例：

```python
@step_plugin(
    id="mycompany.llm_analysis",
    version="1.0.0",
    inputs=["arguments"],
    outputs=["analysis_result"],
    use_llm=True,  # LLM使用フラグ
)
def llm_analysis_plugin(
    ctx: StepContext,
    inputs: StepInputs,
    config: dict,
) -> StepOutputs:
    from analysis_core.services.llm import request_to_chat_ai

    # プロンプトを取得（configから、またはデフォルト）
    prompt = config.get("prompt", "Analyze the following...")
    model = config.get("model", ctx.model)

    # LLMリクエスト
    response = request_to_chat_ai(
        messages=[{"role": "user", "content": prompt}],
        model=model,
        provider=ctx.provider,
    )

    # トークン使用量を記録
    return StepOutputs(
        artifacts={"analysis_result": output_path},
        token_usage=response.get("total_tokens", 0),
        token_input=response.get("prompt_tokens", 0),
        token_output=response.get("completion_tokens", 0),
    )
```

## テスト

プラグインのテスト例：

```python
import pytest
from pathlib import Path
from analysis_core.plugin import StepContext, StepInputs

def test_custom_plugin():
    # テスト用コンテキスト
    ctx = StepContext(
        output_dir=Path("/tmp/test_output"),
        input_dir=Path("/tmp/test_input"),
        dataset="test",
        provider="openai",
        model="gpt-4o-mini",
    )

    # テスト用入力
    inputs = StepInputs(
        artifacts={"arguments": Path("/tmp/test_input/args.csv")},
    )

    # プラグイン実行
    result = custom_step_plugin(ctx, inputs, {"threshold": 0.5})

    # 検証
    assert result.artifacts.get("custom_result") is not None
    assert result.artifacts["custom_result"].exists()
```

## ベストプラクティス

1. **ID命名規則**: `organization.step_name` 形式を使用（例: `mycompany.sentiment_analysis`）

2. **バージョニング**: セマンティックバージョニングを使用（例: `1.0.0`）

3. **入出力の明示**: `inputs` と `outputs` を明確に定義して依存関係を明示

4. **エラーハンドリング**: 適切な例外処理を実装

5. **トークン追跡**: LLM使用時は `token_usage` を正確に報告

6. **設定スキーマ**: `config_schema` でバリデーション可能な設定を定義

## トラブルシューティング

### プラグインが見つからない

```
PluginNotFoundError: Plugin 'mycompany.custom_step' not found
```

解決策：
- manifest.yaml の `id` とコードの `id` が一致しているか確認
- `entry` フィールドのモジュール名と属性名が正しいか確認
- プラグインディレクトリが正しく設定されているか確認

### インポートエラー

```
PluginLoadError: Import error: No module named 'some_dependency'
```

解決策：
- プラグインが必要とする依存関係がインストールされているか確認
- 依存関係を `pyproject.toml` または `requirements.txt` に追加

### 型エラー

```
PluginLoadError: Attribute 'plugin' is not an AnalysisStepPlugin
```

解決策：
- `@step_plugin` デコレータが正しく適用されているか確認
- 関数シグネチャが正しいか確認（`ctx`, `inputs`, `config` の3引数）
