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
- [CLI_QUICKSTART.md](../../docs/CLI_QUICKSTART.md) - コマンドラインからの利用
- [IMPORT_QUICKSTART.md](../../docs/IMPORT_QUICKSTART.md) - Python スクリプトからの利用

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
