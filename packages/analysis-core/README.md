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

### レポート本文の翻訳（多言語表示）

分析が終わった `hierarchical_result.json` の本文を LLM で他言語に翻訳し、`translations` に書き込みます。public-viewer の言語切替（日本語 / English / 한국어）は、表示言語の訳がこのフィールドにあれば本文を差し替え、無ければ元の言語のまま表示します。パイプラインの一部ではなく、分析後に必要な言語だけ追加する後処理です。

```bash
# 意見グループ名・説明・概要・問い・イントロを英語と韓国語に翻訳して上書き
kouchou-translate --result outputs/<name>/hierarchical_result.json --languages en,ko

# 元を残して別ファイルへ書き出す / 対象件数だけ確認する
kouchou-translate --result outputs/<name>/hierarchical_result.json --languages en --output translated.json
kouchou-translate --result outputs/<name>/hierarchical_result.json --languages en --dry-run
```

`python -m analysis_core.translate` でも同じです。プロバイダーとモデルは結果 JSON の `config.provider` / `config.model` を既定にし、`--provider` `--model` `--local-llm-address` で上書きできます（`provider=local` なら Ollama などの OpenAI 互換 API）。API キーは分析時と同じ環境変数を使います。

- 既定で翻訳するのは意見グループ（label / takeaway）、`overview`、`config.question`、`config.intro` です。意見本文は件数が多く費用がかさむため、`--include-arguments` を付けたときだけ翻訳します。意見本文の訳が無い言語では、散布図のホバーや階層リストの意見は元の言語で表示されます。
- 1リクエストに `--batch-size`（既定 10）件をまとめて送り、`--workers`（既定 2）で並列にします。欠けた項目は 1 件ずつ再送し、それでも失敗した項目があれば id と失敗種別だけを示して終了し、ファイルは書き換えません。
- 既に他の言語の訳があればそのまま残し、同じ言語は上書きします。各言語の `meta` に使ったモデルと生成日時を記録します。
- 翻訳の品質は確認してください。意見グループ名は短い見出しとして訳すよう指示していますが、固有名詞や専門用語の訳語は元の言語で確認するのが安全です。

`translations` の形:

```json
{
  "en": {
    "clusters": {"1": {"label": "Transport", "takeaway": "..."}},
    "overview": "...",
    "question": "...",
    "intro": "...",
    "arguments": {"A1_0": "..."},
    "meta": {"provider": "openai", "model": "gpt-4o-mini", "generated_at": "..."}
  }
}
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

広聴AI本体と同じ **GNU Affero General Public License v3 (AGPL-3.0)** です。
ライセンス全文は [LICENSE](LICENSE) を参照してください。

以前のREADMEとパッケージメタデータ（PyPI 0.1.0 / 0.1.2を含む）のMIT表記は誤りです。
`analysis-core` の独立パッケージ化は、ライセンスをMITへ変更するものではありません。
