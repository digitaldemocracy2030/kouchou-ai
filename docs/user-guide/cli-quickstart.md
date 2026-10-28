# クイックスタートガイド

このガイドでは、`kouchou-ai-analysis-core` パッケージを使用してCSVファイルのコメントを分析する手順を説明します。

## 前提条件

- Python 3.12 以上
- OpenAI API キー（ChatGPT Plus とは別に API の課金設定が必要です。[APIの課金と429エラー](../self-hosting/api-billing-and-rate-limits.md)を参照）

## 1. インストール

```bash
# 仮想環境の作成（推奨）
python3.12 -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate  # Windows

# パッケージのインストール
pip install 'kouchou-ai-analysis-core[embeddings,clustering]'
```

インストールの確認：

```bash
kouchou-analyze --version
```

`kouchou-ai-analysis-core` の base install だけでも `import analysis_core` や dry-run は可能ですが、通常の分析パイプラインでは local embedding / clustering 関連 dependency が必要です。迷ったら `"[embeddings,clustering]"` 付きで入れるのが安全です。

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
  }
}
```

`hierarchical_clustering.cluster_nums` は省略可能です。省略した場合は、extraction 後の argument 数に基づいておすすめ値が自動計算されます。

### 設定項目の説明

| 項目 | 説明 |
|------|------|
| `name` | レポートの名前 |
| `question` | 分析の問い（概要生成に使用） |
| `input` | CSVファイル名（拡張子なし、`inputs/` からの相対パス） |
| `model` | 使用するLLMモデル（`gpt-4o-mini`, `gpt-4o` など） |
| `provider` | LLMプロバイダー（`openai`, `azure`, `gemini`, `local`） |
| `is_embedded_at_local` | ローカルでエンベディングを行うか |
| `embedding.model` | 埋め込みモデル。チャット用の `model` とは独立に指定でき、省略時は `text-embedding-3-small`。`provider` が `openai` の場合は `text-embedding-3-small` / `text-embedding-3-large` が選択可能（`gemini` は自動的に `gemini-embedding-001` に解決、`is_embedded_at_local: true` ではローカル埋め込みを使用） |
| `extraction.workers` | 並列処理数 |
| `extraction.limit` | 処理するコメント数の上限。空のコメントを除いた先頭からこの件数だけを分析し、超えた分は分析しない（警告を出す）。省略時は 1000。全件を分析するにはコメント数以上の値を指定する |
| `hierarchical_clustering.cluster_nums` | 階層クラスタリングの各レベルのクラスター数。省略時は extraction 後の argument 数からおすすめ値を自動計算 |

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

`config.json` の `"input": "my-comments"` は、既定では `inputs/my-comments.csv` を指します。別ディレクトリを使いたい場合は `--input-dir` と `--output-dir` で filesystem 上の基準パスを切り替えます。

```bash
kouchou-analyze \
  --config /path/to/project/config.json \
  --input-dir /path/to/project/inputs \
  --output-dir /path/to/project/outputs
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
  [RUN] hierarchical_visualization: no trace of previous run
```

`--dry-run` は単に plan を表示するだけでなく、current CLI path に対する **cheap preflight** も兼ねます。`config.json` の構造、解決された input CSV の存在、入力ヘッダ（最低 `comment-id`, `comment-body`）がここで確認されます。API key 検証や実際のパイプライン実行は行いません。

`hierarchical_visualization` ステップは自己完結型の `report.html` を生成します（Plotly CDN のみ参照、データは inline）。これは CLI でのローカル確認用補助 HTML であり、canonical output は `hierarchical_result.json` です。HTML を生成したくない場合は `--without-html` を指定してください。

### validation only

設定だけ、あるいは入力 CSV だけを明示的に検証したい場合は次を使います。

```bash
kouchou-analyze --config config.json --validate-config
kouchou-analyze --config config.json --validate-input
```

`--validate-input` は current execution path で本当に入力 CSV が必要な場合だけ `inputs/<input>.csv` を検証します。たとえば `--only hierarchical_visualization` のような再利用経路では、入力 CSV を必須にしません。

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
├── hierarchical_result.json    # 最終結果（Webビューア用 / report.html の元データ）
├── report.html                 # CLI ローカル確認用の自己完結型 HTML
├── hierarchical_overview.txt   # AI生成の要約テキスト
├── hierarchical_clusters.csv   # クラスタリング結果
├── hierarchical_initial_labels.csv
├── hierarchical_merge_labels.csv
├── args.csv                    # 抽出された意見
├── embeddings.pkl              # 埋め込みベクトル
├── relations.csv
└── hierarchical_status.json    # 実行ステータス
```

### `report.html` の確認

ブラウザで開くだけで散布図と階層クラスタを閲覧できます。pnpm / Node / docker 不要、API サーバ不要、`file://` でも動作します。

```bash
open outputs/config/report.html  # macOS
# xdg-open outputs/config/report.html  # Linux
```

`config.json` に `"report_url_pattern"` を指定すると、各点クリックで元コメントの URL を開けます（例: `"report_url_pattern": "https://example.com/comments/{comment_id}"`）。

`report.html` は CLI の補助出力であり、Web 配信やストレージ同期の canonical artifact ではありません。プロダクトの viewer は `hierarchical_result.json` を入力として描画します。

### 要約の確認

```bash
cat outputs/config/hierarchical_overview.txt
```

### 結果JSONの確認

```python
import json

with open('outputs/config/hierarchical_result.json', encoding='utf-8') as f:
    data = json.load(f)

print(f"第1階層のクラスター数: {sum(1 for c in data['clusters'] if c['level'] == 1)}")
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
| `--dry-run` | cheap preflight 後に実行計画を表示して終了 |
| `--validate-config` | config の構造だけ検証して終了 |
| `--validate-input` | 解決された input CSV の存在と必須カラムを検証して終了 |
| `--force`, `-f` | 全ステップを強制再実行 |
| `--only`, `-o` | 特定のステップのみ実行 |
| `--without-html` | HTML生成をスキップ |
| `--output-dir` | 出力ディレクトリ（デフォルト: `outputs`） |
| `--input-dir` | 入力ディレクトリ（デフォルト: `inputs`） |

## 8. トラブルシューティング

### `Unknown provider: None`

古い版の analysis-core で、`provider` を書いていない（または `null` の）設定ファイルを使うと出ます。現在の版では `provider` を省略すると `openai` として扱います。古い版を使う場合は、設定ファイルに `"provider": "openai"` を追加してください。

### `'is_embedded_at_local'` エラー

設定ファイルに `"is_embedded_at_local": false` を追加してください。

### `Job already running`

```
Job already running and locked. Try again in 5 minutes.
```

このエラーは、出力先（`outputs/<設定ファイル名>/`。`--output-dir` を指定した場合はその下）の `hierarchical_status.json` で `status` が `running` のままになっていて、ロックの期限（`lock_until`）がまだ切れていないときに出ます。ロックの期限は、実行の進み具合が記録されるたびに「その時点から 5 分後」へ延びます。Ctrl+C で止めた場合は通常、中断として記録されるため、このエラーにはなりません。強制終了（`kill -9` や端末・コンテナの終了など）の直後か、別のプロセスが同じ設定で実際に実行中のときに出ます。

次の順に対処してください。

1. 別の端末などで、同じ設定の分析が動いていないか確認します。動いている場合は、終わるまで待ちます。
2. 動いていなければ、最後の記録から 5 分待って同じコマンドを再実行します。完了済みのステップ（抽出・埋め込みなど）はそのまま再利用され、続きから実行されます（`--dry-run` で `[SKIP] extraction: nothing changed` のように確認できます）。
3. すぐに再開したい場合は、別のプロセスが動いていないことを確かめたうえで、`hierarchical_status.json` の `"status": "running"` を `"status": "error"` に書き換えてから再実行します。

出力ディレクトリや `hierarchical_status.json` は削除しないでください。完了済みステップの記録が消えるため抽出から全件やり直しになり、抽出・埋め込みの API 料金がもう一度かかります。前回の結果も失われます。最初からすべてやり直したい場合は、ロックが切れてから `--force` を付けて実行してください（この場合も API 料金がもう一度かかります）。

### API レート制限（429）

429 エラーには、残高不足（`insufficient_quota`。エラー文に `You exceeded your current quota` を含む）と、レート制限（`Rate limit reached for ...`）の 2 種類があります。見分け方と対処の詳細は[APIの課金と429エラー](../self-hosting/api-billing-and-rate-limits.md)を参照してください。

- **残高不足**: 自動では直りません。OpenAI Platform の Billing で残高と利用上限（usage limit）の両方を確認し、残高が無ければクレジットを購入、上限に達していれば上限を見直してから再実行してください。
- **レート制限（チャット要求）**: 2026-10-27 以降の `main`（analysis-core 0.2.0 より後）では、抽出・意見分類・ラベル生成・要約のチャット要求が 429 を受けると待って送り直し、同時に送る数も自動で下げるので、多くの場合は何もしなくても完走します。各工程の `workers` は同時に送る数の「上限」として扱われます。それでも 429 が続く場合や、それ以前の版を使っている場合は、失敗した工程の `workers` を小さくしてください（例: `1`）。設定は工程ごとに分かれていて、抽出は `extraction.workers`、意見分類は `opinion_classification.workers`、ラベル生成は `hierarchical_initial_labelling.workers` / `hierarchical_merge_labelling.workers`、LLM grouping は `llm_grouping.workers` です（`extraction.workers` を下げても他の工程には効きません）。完了済みのステップは再利用されるので、上の `Job already running` の項と同様に続きから再実行できます。
- **レート制限（埋め込み）**: 埋め込み（`embedding` ステップ）の要求はこの自動調整の対象外で、SDK の短い再試行だけです。429 で失敗した場合は時間をおいて再実行してください（完了済みの抽出は再利用されます）。`is_embedded_at_local: true` でローカル埋め込みに切り替えると、外部 API のレート制限を受けません。

## 9. 発展的な使い方

### UMAP 平面を使い回す（別レポートと同じ散布図座標にそろえる）

散布図の点の配置は UMAP による次元圧縮で決まりますが、UMAP は確率的なため、**同じデータでも実行するたびに平面（軸・配置）が変わります**。そのため「先月のデータと今月のデータを同じ平面に並べて変化を見る」といった比較がしにくくなります。

CLI で分析を実行すると、使用した UMAP モデルが各レポートの出力先に `outputs/<レポート名>/umap_model.pkl` として保存されます（`hierarchical_clustering.save_umap_model` が `false` のときは保存しません。後述）。新しいレポートを作るときに既存レポートのモデルを指定すると、UMAP を学習し直さず（`fit_transform` ではなく）既存の平面へ `transform` で投影するため、**同じ座標平面上に別データを並べられます**。

> この機能は現状 CLI 専用です。WebUI（管理画面）からは提供していません。
> 管理画面で作成・複製したレポートは、既定で `save_umap_model: false` で実行されるため `umap_model.pkl` が無く、投影元には使えません（複製元の config ファイルに `save_umap_model: true` を明示していた場合だけは、複製でもその値を引き継いで保存します）。投影元にするレポートは CLI で作成してください。

`hierarchical_clustering.reuse_umap_model` に、使い回したい既存レポートを指定します。

```json
{
  "input": "report_october",
  "question": "10月のデータ",
  "hierarchical_clustering": {
    "reuse_umap_model": "report_september"
  }
}
```

`cluster_nums` は省略できます。省略した場合は「3. 設定ファイルの作成」と同じく、このレポートの argument 数からおすすめ値が自動計算されます（元レポートのクラスタ数は引き継ぎません）。元レポートと粒度をそろえたいときだけ明示してください。

`reuse_umap_model` には、次のいずれか 1 つの書き方で文字列を指定します。絶対パスはそのまま使います。レポート名・相対パスの場合は `outputs/<値>`、`outputs/<値>/umap_model.pkl` の順に探し、最初に見つかったファイルを使います:

| 書き方 | 解決されるパス | 用途 |
|--------|----------------|------|
| `"report_september"`（レポート名） | `outputs/report_september/umap_model.pkl` | 同じ `outputs` 配下の別レポートを使う（最も手軽） |
| `"report_september/umap_model.pkl"`（相対パス） | `outputs/report_september/umap_model.pkl` | 出力先配下のパスを明示する |
| `"/abs/path/umap_model.pkl"`（絶対パス） | そのまま | 別の場所に保存したモデルを使う |

注意点:

- **元レポートと同じ埋め込みモデル**（`embedding.model`）で生成した埋め込みが必要です。次元が一致しないとエラーで停止します。
- 指定した `umap_model.pkl` が見つからない場合は、黙って新しい平面を学習し直すのではなく、エラーで停止します（指定ミスに気づけるようにするため）。
- このレポート自身のモデルも `outputs/<レポート名>/umap_model.pkl` に保存されるため、さらに別のレポートの投影元として再利用できます。
- `"save_umap_model": false` を指定すると、このレポートの `umap_model.pkl` を保存しません（前回の実行で残ったものも削除します）。モデルには入力の埋め込みの写しが入り、件数に比例して大きくなる（数万件で GB 単位）ので、投影元に使わないレポートで容量を抑えたいときに指定します。
- 後から `save_umap_model` を `true` に戻しても、それだけでは clustering は再実行されず、モデルは作られません。`-f` や `--only hierarchical_clustering` で作り直すと UMAP を学習し直すので、平面は元のレポートの散布図とは別のものになります。投影元にしたいレポートは、最初から保存する設定で作ってください。

実行は通常どおりです:

```bash
kouchou-analyze --config report_october.json
```

### 所与の分類枠へ意見を分類する（指定カテゴリ分類 / LLM grouping）

あらかじめ決めたカテゴリに意見を割り当てたい場合は、`analysis_mode` を `llm_grouping` にし、`llm_grouping.predefined_groups` にカテゴリを与えます。クラスタを自動発見する代わりに、**枠は人間が与え、各意見の割当だけを LLM が行います**。

```json
{
  "input": "my-comments",
  "question": "住みやすい街にするには？",
  "analysis_mode": "llm_grouping",
  "llm_grouping": {
    "predefined_groups": [
      { "label": "交通", "description": "公共交通・道路・移動に関する意見" },
      { "id": "park", "label": "公園・緑地", "description": "公園整備や緑地に関する意見" },
      { "label": "子育て・教育", "description": "保育・学校・子育て支援に関する意見" }
    ]
  }
}
```

- 各カテゴリは `label`（必須）と `description`（任意だが推奨。割当精度が上がります）を持ちます。`id` を省略すると `g1`, `g2`, … が自動採番されます。
- **「その他」カテゴリは必ず自動で追加されます**（指定不要・削除不可）。どのカテゴリにも明確に当てはまらない意見は、無理に押し込めず「その他」に分類されます。「その他」に多くの意見が集まる場合は、分類枠に過不足があるサインです。
- ラベルを変えたい場合は `llm_grouping.other_group_label`（既定 `"その他"`）で指定できます。自分で同名または `id: "other"` のカテゴリを定義した場合は、それが受け皿として使われ二重には追加されません。
- 散布図の座標は従来どおり埋め込みから計算されるため、ビューアはそのまま利用できます。

> この機能は現状 CLI 専用です。WebUI（管理画面）からの指定カテゴリ分類は今後の対応予定です。

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

### 意見ごとに侮辱・ヘイト表現 / 政策提案のラベルを付ける

意見1件ごとにLLMで yes/no のラベルを付け、ビューアの属性フィルタで絞り込めるようにします。意見1件につきLLM呼び出しが1回増えます。定義と注意点は [意見の分類ラベル](../development/opinion-classification.md) を参照してください。

```json
{
  "opinion_classification": {
    "enabled": true,
    "workers": 3
  }
}
```

出力は `opinion_classifications.csv`（意見ごとの `yes` / `no`）と `opinion_classification_summary.json`（件数と比率）です。比率はLLMの判定に基づく、定義に対する割合であり、人手で検証したものではありません。

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

チャット用の環境変数が必要です。埋め込みも Azure で行う場合（`"is_embedded_at_local": false`）は、埋め込み用も必要です。どちらも `AZURE_OPENAI_*` ではありません。

```bash
# チャット（意見の抽出・ラベル付け・要約）
export AZURE_CHATCOMPLETION_ENDPOINT="https://your-resource.openai.azure.com"
export AZURE_CHATCOMPLETION_DEPLOYMENT_NAME="your-chat-deployment-name"
export AZURE_CHATCOMPLETION_VERSION="2024-10-21"
export AZURE_CHATCOMPLETION_API_KEY="your-key"
# 推論モデル（o 系 / GPT-5,6 系）をモデル名と違うデプロイ名で使う場合は、実モデル ID も設定する
# （推論モデルには temperature を送らないため。実モデル名とデプロイ名のどちらかが推論モデル名なら推論とみなす。
#   表示名ではなく gpt-5-mini のようなモデル ID を入れる。名前によらず指定するなら AZURE_CHATCOMPLETION_REASONING=true / false）
# export AZURE_CHATCOMPLETION_MODEL_NAME="gpt-5-mini"

# 埋め込み（"is_embedded_at_local": true なら不要）
export AZURE_EMBEDDING_ENDPOINT="https://your-resource.openai.azure.com"
export AZURE_EMBEDDING_DEPLOYMENT_NAME="your-embedding-deployment-name"
export AZURE_EMBEDDING_VERSION="2023-05-15"
export AZURE_EMBEDDING_API_KEY="your-key"
```

```json
{
  "provider": "azure",
  "model": "gpt-4o-mini"
}
```

Azure では、実際に使うモデルは `model` ではなく、環境変数のデプロイ名で決まります。

### Gemini を使用する

```bash
pip install 'kouchou-ai-analysis-core[gemini,embeddings,clustering]'
export GEMINI_API_KEY="your-key"
```

```json
{
  "provider": "gemini",
  "model": "gemini-2.5-flash"
}
```

## 10. output validation の位置づけ

`hierarchical_result.json` などの **出力 artifact の厳密検証** は、current `analysis-core` では runtime の success 条件にはしていません。ここは end-user CLI を重くするより、schema test / e2e / viewer 側の利用で担保する寄りにしてあります。

つまり CLI の preflight は `config` と `input` の fail-fast に集中し、post-run artifact validation は主に **developer/test concern** として扱います。

## 11. 結果の可視化

結果JSONは Matplotlib 等で可視化できます：

```python
import json
import matplotlib.pyplot as plt

with open('outputs/config/hierarchical_result.json', encoding='utf-8') as f:
    data = json.load(f)

# クラスターごとの意見数を棒グラフで表示（意見数は value に入っている）
clusters = [c for c in data['clusters'] if c['level'] == 1]
labels = [c['label'][:20] + '...' if len(c['label']) > 20 else c['label'] for c in clusters]
counts = [c['value'] for c in clusters]

plt.figure(figsize=(10, 6))
plt.barh(labels, counts)
plt.xlabel('意見数')
plt.title('クラスター別意見数')
plt.tight_layout()
plt.savefig('cluster_chart.png')
plt.show()
```

---

詳細なAPIドキュメントは packages/analysis-core/README.md を参照してください。
