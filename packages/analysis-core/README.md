# kouchou-ai-analysis-core

広聴AIの分析パイプラインコアライブラリ。

## 概要

このパッケージは、コメントデータを分析し、クラスタリングと要約を行うパイプラインを提供します。

## 必要条件

- Python 3.12以上

## インストール

```bash
pip install kouchou-ai-analysis-core
```

Geminiサポートを含める場合:
```bash
pip install kouchou-ai-analysis-core[gemini]
```

## 使用方法

詳細なチュートリアルは以下を参照してください：
- [CLIクイックスタート](https://digitaldemocracy2030.github.io/kouchou-ai/user-guide/cli-quickstart/) - コマンドラインからの利用
- [インポート方法](https://digitaldemocracy2030.github.io/kouchou-ai/user-guide/import-quickstart/) - Python スクリプトからの利用

### CLI

```bash
kouchou-analyze --config config.json
```

### ライブラリとして

```python
from analysis_core import PipelineOrchestrator, PipelineConfig

config = PipelineConfig.from_json("config.json")
orchestrator = PipelineOrchestrator(config.to_dict())
result = orchestrator.run()
```

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

詳細は [プラグイン開発ガイド](https://digitaldemocracy2030.github.io/kouchou-ai/development/plugin-guide/) を参照してください。

## 開発

```bash
# 依存関係のインストール
pip install -e ".[dev]"

# テストの実行
pytest

# リンターの実行
ruff check .
```

## ライセンス

MIT License
