# ファイルシステムベース実行ガイド

このドキュメントでは、APIサーバーを起動せずに、ファイルシステム上のデータを使用して広聴AIのパイプラインを直接実行する方法を説明します。

## 概要

広聴AIのパイプラインは、`hierarchical_main.py`を直接実行することで、APIサーバーなしで動作させることができます。この方法は以下のような場合に有用です：

- ローカル環境でのテストや開発
- バッチ処理での大量データ処理
- CI/CDパイプラインでの自動テスト
- APIサーバーのオーバーヘッドを避けたい場合

## ディレクトリ構造

```
server/broadlistening/pipeline/
├── hierarchical_main.py      # メインエントリーポイント
├── configs/                  # 設定JSONファイル
│   ├── dummy-comments-japan.json
│   └── example-polis.json
├── inputs/                   # 入力CSVファイル
│   ├── dummy-comments-japan.csv
│   └── example-polis.csv
└── outputs/                  # 出力ディレクトリ
    └── {dataset}/            # データセット名ごとのディレクトリ
        ├── hierarchical_result.json
        ├── hierarchical_status.json
        ├── args.csv
        ├── embeddings.pkl
        └── ...
```

## 入力ファイル形式

### 1. CSVファイル（コメントデータ）

**配置場所**: `server/broadlistening/pipeline/inputs/{dataset}.csv`

**必須カラム**:
- `comment-id`: コメントの一意識別子（整数）
- `comment-body`: コメント本文（文字列）

**オプションカラム**:
設定JSONの`extraction.properties`で指定したカラムは必須になります。例：
- `source`: コメントの出典
- `age`: 回答者の年齢
- その他任意のプロパティ

**文字エンコーディング**: UTF-8推奨（Shift-JIS、CP932も対応）

**例**:
```csv
comment-id,comment-body,source,age
1,We need more investment in renewable energy.,Google Form,20
2,Expanding childcare support is essential.,Google Form,21
3,Promote startup ecosystems to drive innovation.,X API,22
```

### 2. 設定JSONファイル

**配置場所**: `server/broadlistening/pipeline/configs/{dataset}.json`

**必須フィールド**:
- `name`: レポート名（文字列）
- `question`: 分析の問い（文字列）
- `input`: 入力CSVファイル名（拡張子なし）

**オプションフィールド**:
- `model`: 使用するLLMモデル（デフォルト: `gpt-4o-mini`）
- `provider`: LLMプロバイダー（`openai`, `azure`, `gemini`, `openrouter`, `local`）
- `intro`: レポートの導入文
- `is_pubcom`: 公開コメントかどうか（boolean）
- `is_embedded_at_local`: ローカルで埋め込みを生成するか（boolean）
- `local_llm_address`: ローカルLLMのアドレス
- `enable_source_link`: ソースリンクを有効にするか（boolean）

**ステップ別設定**:

各パイプラインステップに対して、個別の設定を指定できます：

#### extraction（意見抽出）
```json
"extraction": {
  "workers": 3,              // 並列処理数
  "limit": 20,               // 処理するコメント数の上限
  "properties": [            // CSVから引き継ぐプロパティ
    "source",
    "age"
  ],
  "categories": {            // カテゴリ分類（オプション）
    "sentiment": {
      "positive": "肯定的な意見につけるカテゴリ",
      "negative": "否定的な意見につけるカテゴリ",
      "neutral": "中立的な意見につけるカテゴリ"
    }
  },
  "category_batch_size": 5   // カテゴリ分類のバッチサイズ
}
```

#### embedding（埋め込み生成）
```json
"embedding": {
  "model": "text-embedding-3-small"  // 埋め込みモデル
}
```

#### hierarchical_clustering（階層的クラスタリング）
```json
"hierarchical_clustering": {
  "cluster_nums": [3, 6]    // 各階層のクラスタ数
}
```

#### hierarchical_initial_labelling（初期ラベル付け）
```json
"hierarchical_initial_labelling": {
  "sampling_num": 3,        // サンプリング数
  "workers": 1              // 並列処理数
}
```

#### hierarchical_merge_labelling（ラベルマージ）
```json
"hierarchical_merge_labelling": {
  "sampling_num": 3,        // サンプリング数
  "workers": 1              // 並列処理数
}
```

#### hierarchical_aggregation（結果集約）
```json
"aggregation": {
  "sampling_num": 5000,     // サンプリング数
  "hidden_properties": {    // 非表示にするプロパティ値
    "source": ["X API"],
    "age": [20, 25]
  }
}
```

**完全な設定例**:
```json
{
  "name": "日本の未来について",
  "question": "日本の未来に対してどんな意見が寄せられているのか？",
  "input": "dummy-comments-japan",
  "model": "gpt-4o-mini",
  "provider": "openai",
  "extraction": {
    "workers": 3,
    "limit": 20,
    "properties": ["source", "age"]
  },
  "hierarchical_clustering": {
    "cluster_nums": [3, 6]
  },
  "intro": "このレポートは日本の未来に関する意見を分析したものです。"
}
```

## 実行方法

### 基本的な実行

```bash
cd server/broadlistening/pipeline
python hierarchical_main.py configs/{dataset}.json
```

例：
```bash
python hierarchical_main.py configs/dummy-comments-japan.json
```

### コマンドラインオプション

#### `-f, --force`
すべてのステップを強制的に再実行します。

```bash
python hierarchical_main.py configs/dummy-comments-japan.json -f
```

#### `-o, --only`
特定のステップのみを実行します。

```bash
python hierarchical_main.py configs/dummy-comments-japan.json -o extraction
```

利用可能なステップ名：
- `extraction`
- `embedding`
- `hierarchical_clustering`
- `hierarchical_initial_labelling`
- `hierarchical_merge_labelling`
- `hierarchical_overview`
- `hierarchical_aggregation`
- `hierarchical_visualization`

#### `--skip-interaction`
確認プロンプトをスキップして即座に実行します。

```bash
python hierarchical_main.py configs/dummy-comments-japan.json --skip-interaction
```

#### `--without-html`
HTML出力（visualization）をスキップします。

```bash
python hierarchical_main.py configs/dummy-comments-japan.json --without-html
```

### 複数オプションの組み合わせ

```bash
python hierarchical_main.py configs/dummy-comments-japan.json -f --skip-interaction
```

## 環境変数の設定

パイプラインを実行する前に、必要な環境変数を設定してください。

### 必須環境変数

LLMプロバイダーに応じて、以下のいずれかが必要です：

```bash
# OpenAI使用時
export OPENAI_API_KEY="your-api-key"

# Azure OpenAI使用時
export AZURE_OPENAI_API_KEY="your-api-key"
export AZURE_OPENAI_ENDPOINT="your-endpoint"

# Google Gemini使用時
export GEMINI_API_KEY="your-api-key"

# OpenRouter使用時
export OPENROUTER_API_KEY="your-api-key"
```

### .envファイルの使用

プロジェクトルート（`kouchou-ai/`）に`.env`ファイルを作成することで、環境変数を管理できます：

```bash
# .env
OPENAI_API_KEY=your-api-key
GEMINI_API_KEY=your-api-key
```

## 出力ファイル

パイプラインの実行により、以下のファイルが`outputs/{dataset}/`ディレクトリに生成されます：

### 最終出力

#### `hierarchical_result.json`
最終的な分析結果を含むJSONファイル。以下の構造を持ちます：

```json
{
  "arguments": [
    {
      "arg_id": "A0_0",
      "argument": "抽出された意見テキスト",
      "comment_id": 0,
      "x": 3.85,
      "y": -3.57,
      "p": 0,
      "cluster_ids": ["0", "1_5", "2_9"]
    }
  ],
  "clusters": [
    {
      "id": "0",
      "label": "クラスタのラベル",
      "description": "クラスタの説明",
      "level": 0
    }
  ],
  "propertyMaps": {
    "source": {
      "Google Form": ["A0_0", "A1_0"],
      "X API": ["A2_0"]
    }
  },
  "intro": "レポートの導入文",
  "overview": "全体の概要"
}
```

#### `hierarchical_status.json`
パイプラインの実行状態を記録するファイル：

```json
{
  "status": "completed",
  "start_time": "2024-01-01T10:00:00",
  "end_time": "2024-01-01T10:30:00",
  "total_token_usage": 15000,
  "token_usage_input": 10000,
  "token_usage_output": 5000,
  "estimated_cost": 0.025,
  "completed_jobs": [
    {
      "step": "extraction",
      "completed": "2024-01-01T10:05:00",
      "duration": 300,
      "token_usage": 5000
    }
  ]
}
```

### 中間ファイル

各ステップで以下の中間ファイルが生成されます：

- `args.csv`: 抽出された意見のリスト
- `relations.csv`: コメントと意見の関係
- `embeddings.pkl`: 意見の埋め込みベクトル
- `hierarchical_clusters.csv`: クラスタリング結果
- `hierarchical_initial_labels.csv`: 初期ラベル
- `hierarchical_merge_labels.csv`: マージされたラベル
- `hierarchical_overview.txt`: 概要テキスト

## パイプライン処理フロー

パイプラインは以下の8つのステップを順番に実行します：

1. **extraction**: コメントから意見を抽出
2. **embedding**: 意見の埋め込みベクトルを生成
3. **hierarchical_clustering**: 階層的クラスタリングを実行
4. **hierarchical_initial_labelling**: 各クラスタにラベルを付与
5. **hierarchical_merge_labelling**: 階層間でラベルをマージ
6. **hierarchical_overview**: 全体の概要を生成
7. **hierarchical_aggregation**: 結果をJSON形式に集約
8. **hierarchical_visualization**: 可視化用HTMLを生成

各ステップは、依存する前のステップが完了している場合にのみ実行されます。`-f`オプションを使用すると、すべてのステップを強制的に再実行できます。

## トラブルシューティング

### エラー: "Missing required field 'input' in config"

設定JSONファイルに`input`フィールドが含まれていません。必須フィールドを確認してください。

### エラー: "Properties [...] not found in comments"

設定JSONの`extraction.properties`で指定したカラムがCSVファイルに存在しません。CSVファイルのカラム名を確認してください。

### エラー: "Job already running and locked"

別のプロセスがパイプラインを実行中です。5分待つか、`outputs/{dataset}/hierarchical_status.json`を削除してください。

### エラー: "result is empty, maybe bad prompt"

意見の抽出に失敗しました。プロンプトの内容やLLMモデルの設定を確認してください。

### 文字化けが発生する

CSVファイルのエンコーディングを確認してください。UTF-8を推奨します。

### トークン使用量が多すぎる

- `extraction.limit`を減らしてコメント数を制限
- `extraction.workers`を減らして並列処理数を削減
- より小さいモデル（例: `gpt-4o-mini`）を使用

## ベストプラクティス

1. **小規模データでテスト**: 最初は`extraction.limit`を10-20に設定してテスト実行
2. **段階的な実行**: `-o`オプションで各ステップを個別に確認
3. **ステータスファイルの確認**: `hierarchical_status.json`でトークン使用量とコストを確認
4. **バックアップ**: 重要なデータは実行前にバックアップ
5. **環境変数の管理**: `.env`ファイルでAPIキーを安全に管理

## 参考資料

- [パイプライン詳細説明](./README.md)
- [設定スキーマ定義](./pipeline/schemas/config_schema.py)
- [入力スキーマ定義](./pipeline/schemas/input_csv_schema.py)
- [出力スキーマ定義](./pipeline/schemas/output_schema.py)
