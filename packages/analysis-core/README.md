# kouchou-ai-analysis-core

広聴AIの分析パイプラインコアライブラリ。

## 概要

このパッケージは、コメントデータを分析し、クラスタリングと要約を行うパイプラインを提供します。

## 必要条件

- Python 3.12以上

## インストール

```bash
pip install 'kouchou-ai-analysis-core[embeddings,clustering]'
```

Geminiサポートを含める場合:
```bash
pip install 'kouchou-ai-analysis-core[gemini,embeddings,clustering]'
```

軽量な base install だけ欲しい場合:
```bash
pip install kouchou-ai-analysis-core
```

この場合でも `import analysis_core` や dry-run はできますが、local embedding や hierarchical clustering を実行するには対応する extras が必要です。

## 使用方法

詳細なチュートリアルは以下を参照してください：
- [CLIクイックスタート](../../docs/user-guide/cli-quickstart.md) - コマンドラインからの利用
- [インポート方法](../../docs/user-guide/import-quickstart.md) - Python スクリプトからの利用

### CLI

```bash
kouchou-analyze --config config.json
```

CLI の canonical output は `hierarchical_result.json` です。既定ではローカル確認用の補助 HTML として `report.html` も生成しますが、これは保存・配信の対象ではありません。

### ライブラリとして

```python
from analysis_core import PipelineOrchestrator, PipelineConfig

config = PipelineConfig.from_json("config.json")
orchestrator = PipelineOrchestrator.from_dict(config.to_dict())
result = orchestrator.run_default()
```

`run_default()` が current の canonical path です。`run()` も残っていますが、legacy direct-step 実行経路として deprecated 扱いです。

## プラグインシステム

analysis-core は拡張可能なプラグインアーキテクチャを採用しています。

### カスタムプラグインの作成

```python
from analysis_core.plugin import step_plugin, StepContext, StepInputs, StepOutputs

@step_plugin(
    id="mycompany.custom_step",
    version="1.0.0",
    inputs=["arguments"],
    outputs=["custom_result"],
)
def custom_step(ctx: StepContext, inputs: StepInputs, config: dict) -> StepOutputs:
    # カスタム処理
    output_path = ctx.output_dir / "custom_result.csv"
    return StepOutputs(artifacts={"custom_result": output_path})
```

### 外部プラグインの配置

```
plugins/analysis/
└── my-plugin/
    ├── manifest.yaml
    └── plugin.py
```

詳細は [プラグイン開発ガイド](../../docs/development/plugin-guide.md) を参照してください。

## 開発

```bash
# 依存関係のインストール
pip install -e ".[dev,embeddings,clustering]"

# テストの実行
pytest

# リンターの実行
ruff check .
```

## ライセンス

MIT License
