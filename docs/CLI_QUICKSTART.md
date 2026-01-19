# クイックスタートガイド

このガイドでは、`kouchou-ai-analysis-core` パッケージを使用してCSVファイルのコメントを分析する手順を説明します。

## 前提条件

- Python 3.12 以上
- OpenAI API キー

## 1. インストール

```bash
# 仮想環境の作成（推奨）
python3.12 -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate  # Windows

# パッケージのインストール
pip install kouchou-ai-analysis-core
```

インストールの確認：

```bash
kouchou-analyze --version
```

## 2. 入力CSVの準備

CSVファイルには以下のカラムが必要です：

| カラム名 | 必須 | 説明 |
|---------|------|------|
| `comment-id` | ✅ | コメントの一意なID |
| `comment-body` | ✅ | コメント本文 |
| その他 | - | 任意の属性（source, age など） |

例：`inputs/my-comments.csv`

```csv
comment-id,comment-body,source
1,公園に新しい遊具がほしいです,アンケート
2,駅前の駐輪場を増やしてください,メール
3,保育園の待機児童を解消してほしい,アンケート
4,自転車の通行レーンを整備してください,メール
5,子育て支援を充実させてください,アンケート
```

## 3. 設定ファイルの作成

`config.json` を作成します：

```json
{
  "name": "市民意見分析",
  "question": "市民からどのような意見が寄せられていますか？",
  "input": "my-comments",
  "model": "gpt-4o-mini",
  "provider": "openai",
  "is_embedded_at_local": false,
  "extraction": {
    "workers": 3,
    "limit": 100
  },
  "hierarchical_clustering": {
    "cluster_nums": [3, 6]
  }
}
```

### 設定項目の説明

| 項目 | 説明 |
|------|------|
| `name` | レポートの名前 |
| `question` | 分析の問い（概要生成に使用） |
| `input` | CSVファイル名（拡張子なし、`inputs/` からの相対パス） |
| `model` | 使用するLLMモデル（`gpt-4o-mini`, `gpt-4o` など） |
| `provider` | LLMプロバイダー（`openai`, `azure`, `gemini`, `local`） |
| `is_embedded_at_local` | ローカルでエンベディングを行うか |
| `extraction.workers` | 並列処理数 |
| `extraction.limit` | 処理するコメント数の上限 |
| `hierarchical_clustering.cluster_nums` | 階層クラスタリングの各レベルのクラスター数 |

## 4. 環境変数の設定

OpenAI API キーを設定します：

```bash
export OPENAI_API_KEY="sk-your-api-key-here"
```

または `.env` ファイルを作成：

```
OPENAI_API_KEY=sk-your-api-key-here
```

## 5. 分析の実行

### ディレクトリ構成

```
my-project/
├── config.json
├── inputs/
│   └── my-comments.csv
└── outputs/          # 自動生成される
```

### 実行前の確認（dry-run）

```bash
kouchou-analyze --config config.json --dry-run
```

出力例：
```
Execution Plan:
----------------------------------------
  [RUN] extraction: no trace of previous run
  [RUN] embedding: no trace of previous run
  [RUN] hierarchical_clustering: no trace of previous run
  [RUN] hierarchical_initial_labelling: no trace of previous run
  [RUN] hierarchical_merge_labelling: no trace of previous run
  [RUN] hierarchical_overview: no trace of previous run
  [RUN] hierarchical_aggregation: no trace of previous run
  [SKIP] hierarchical_visualization: skipping html output
```

### 分析の実行

```bash
kouchou-analyze --config config.json
```

実行中の出力：
```
Starting pipeline execution...
  Config: config.json
  Output: outputs

Running step: extraction
100%|██████████| 5/5 [00:08<00:00,  1.67s/it]
Running step: embedding
Running step: hierarchical_clustering
Running step: hierarchical_initial_labelling
Running step: hierarchical_merge_labelling
Running step: hierarchical_overview
Running step: hierarchical_aggregation

Pipeline completed successfully!
Duration: 45.16 seconds
Total token usage: 11765
Output directory: outputs/config
```

## 6. 結果の確認

出力ディレクトリ構成：

```
outputs/config/
├── hierarchical_result.json    # 最終結果（Webビューア用）
├── hierarchical_overview.txt   # AI生成の要約テキスト
├── hierarchical_clusters.csv   # クラスタリング結果
├── hierarchical_initial_labels.csv
├── hierarchical_merge_labels.csv
├── args.csv                    # 抽出された意見
├── embeddings.pkl              # 埋め込みベクトル
├── relations.csv
└── hierarchical_status.json    # 実行ステータス
```

### 要約の確認

```bash
cat outputs/config/hierarchical_overview.txt
```

### 結果JSONの確認

```python
import json

with open('outputs/config/hierarchical_result.json') as f:
    data = json.load(f)

print(f"クラスター数: {len(data['clusters'])}")
print(f"コメント数: {data['comment_num']}")
print(f"要約: {data['overview']}")
```

## 7. CLIオプション一覧

```bash
kouchou-analyze --help
```

| オプション | 説明 |
|-----------|------|
| `--config`, `-c` | 設定ファイルのパス（必須） |
| `--dry-run` | 実行計画のみ表示 |
| `--force`, `-f` | 全ステップを強制再実行 |
| `--only`, `-o` | 特定のステップのみ実行 |
| `--output-dir` | 出力ディレクトリ（デフォルト: `outputs`） |
| `--input-dir` | 入力ディレクトリ（デフォルト: `inputs`） |

## 8. トラブルシューティング

### `Unknown provider: None`

設定ファイルに `"provider": "openai"` を追加してください。

### `'is_embedded_at_local'` エラー

設定ファイルに `"is_embedded_at_local": false` を追加してください。

### `Job already running`

前回の実行が中断された場合、ロックファイルが残っています：

```bash
rm -rf outputs/config
```

### API レート制限

`extraction.workers` を小さくしてください（例: `1`）。

## 9. 発展的な使い方

### カテゴリ分類の追加

```json
{
  "extraction": {
    "workers": 3,
    "limit": 100,
    "categories": {
      "sentiment": {
        "positive": "肯定的な意見",
        "negative": "否定的な意見",
        "neutral": "中立的な意見"
      },
      "topic": {
        "infrastructure": "インフラに関する意見",
        "welfare": "福祉に関する意見",
        "education": "教育に関する意見"
      }
    }
  }
}
```

### 特定の属性値を非表示にする

```json
{
  "hierarchical_aggregation": {
    "hidden_properties": {
      "source": ["internal"],
      "age": [0, 999]
    }
  }
}
```

### Azure OpenAI を使用する

```bash
export AZURE_OPENAI_API_KEY="your-key"
export AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com/"
export AZURE_OPENAI_DEPLOYMENT="your-deployment-name"
```

```json
{
  "provider": "azure",
  "model": "gpt-4o-mini"
}
```

### Gemini を使用する

```bash
pip install 'kouchou-ai-analysis-core[gemini]'
export GOOGLE_API_KEY="your-key"
```

```json
{
  "provider": "gemini",
  "model": "gemini-1.5-flash"
}
```

## 10. 結果の可視化

結果JSONは Matplotlib 等で可視化できます：

```python
import json
import matplotlib.pyplot as plt

with open('outputs/config/hierarchical_result.json') as f:
    data = json.load(f)

# クラスターごとの意見数を棒グラフで表示
clusters = [c for c in data['clusters'] if c.get('level') == 1]
labels = [c['label'][:20] + '...' for c in clusters]
counts = [len(c.get('arguments', [])) for c in clusters]

plt.figure(figsize=(10, 6))
plt.barh(labels, counts)
plt.xlabel('意見数')
plt.title('クラスター別意見数')
plt.tight_layout()
plt.savefig('cluster_chart.png')
plt.show()
```

---

詳細なAPIドキュメントは [packages/analysis-core/README.md](../README.md) を参照してください。
