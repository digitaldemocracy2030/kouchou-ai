# 入力プラグインと分析プラグインの出力データ構造

このドキュメントは、**入力プラグインが生成するCSV**と、**analysis-core の各分析ステップが出力するアーティファクト**の構造を整理したものです。
データ連携やカスタムプラグイン作成時の参照用に使ってください。

## 共通ルール

- 入力CSVは `inputs/{ファイル名}.csv` に保存されます。
- 分析ステップの出力は `outputs/{dataset}/` 配下に生成されます。
- CSVはヘッダー付き・UTF-8を前提にしています。
- IDは基本的に文字列として扱います（`comment-id`, `arg-id`, `cluster-level-*-id` など）。

---

## 入力プラグインの出力（`inputs/*.csv`）

入力プラグインの `fetch_data()` は `polars.DataFrame` を返し、`save_to_csv()` により `inputs/{name}.csv` として保存されます。

### 必須カラム（実運用で必ず必要）

| カラム名 | 型 | 説明 |
|---|---|---|
| `comment-id` | string | コメントの一意ID（文字列推奨） |
| `comment-body` | string | コメント本文 |

#### `comment-id` が無い場合の扱い

運用経路によって自動生成の有無が異なります。

- **WebUIのCSVアップロード**: フロント側で `id` / `comment-id` が無い場合に自動採番され、最終的に `comment-id` として保存されます。あわせて文字コードを検出して UTF-8 に変換するため、ExcelのShift_JIS（SJIS）CSVも読み込み可能です。
- **スプレッドシート取り込み**: サーバー側で `comment-id` が無い場合に `id-1`, `id-2` のように自動生成されます。
- **入力プラグイン / 直接CSV投入 / CLI**: 自動生成はされないため、**`comment-id` を必ず含めてください**。

### オプションカラム

| カラム名 | 型 | 説明 |
|---|---|---|
| `source` | string | 入力元の名称（例: `YouTube`, `Twitter`） |
| `url` | string | 元コメントへのURL（`enable_source_link` 有効時に使用） |

### 任意属性カラム

`attribute_` プレフィックスを付けると追加属性として扱われます。
これらは `hierarchical_result.json` の `arguments[].attributes` に引き継がれます。

例:

```csv
comment-id,comment-body,source,url,attribute_author,attribute_like_count
c1,公園に新しい遊具がほしいです,アンケート,,山田太郎,12
c2,駅前の駐輪場を増やしてください,Twitter,https://...,@user,5
```

---

## 分析プラグイン（analysis-core）の出力

analysis-core の標準ワークフローは、次のステップでファイルを生成します。
各ステップは **ファイルベースのアーティファクト**を出力します。

### 出力サマリ（標準ステップ）

| プラグインID | 主な出力 | 形式 |
|---|---|---|
| `analysis.extraction` | `args.csv`, `relations.csv` | CSV |
| `analysis.opinion_classification`（任意） | `opinion_classifications.csv`, `opinion_classification_summary.json` | CSV / JSON |
| `analysis.embedding` | `embeddings.pkl` | pickle |
| `analysis.hierarchical_clustering` | `hierarchical_clusters.csv` | CSV |
| `analysis.hierarchical_initial_labelling` | `hierarchical_initial_labels.csv` | CSV |
| `analysis.hierarchical_merge_labelling` | `hierarchical_merge_labels.csv` | CSV |
| `analysis.hierarchical_overview` | `hierarchical_overview.txt` | text |
| `analysis.hierarchical_aggregation` | `hierarchical_result.json` | JSON |
| `analysis.hierarchical_visualization` | HTML/静的レポート | directory |

---

### 1) `analysis.extraction`

**出力1: `args.csv`**

| カラム名 | 型 | 説明 |
|---|---|---|
| `arg-id` | string | 抽出意見のID（`A{comment-id}_{index}` 形式） |
| `argument` | string | 抽出された意見本文 |

**出力2: `relations.csv`**

| カラム名 | 型 | 説明 |
|---|---|---|
| `arg-id` | string | 抽出意見ID |
| `comment-id` | string | 元コメントID |

`relations.csv` は **コメントと意見の対応表**です。1つのコメントから複数意見が抽出されるため、1対多になります。別々のコメントから同じ文面の意見が抽出されても、コメントごとに別の `arg-id` を付けます（意見1件は常に1つのコメントに対応し、`arguments[].attributes` / `url` がそのコメントのものになる）。

> 注: 追加の属性や分類結果を `args.csv` に付与したい場合は、
> カスタムステップで `args.csv` を拡張してから `analysis.hierarchical_aggregation` に渡してください。

---

### 1b) `analysis.opinion_classification`（任意）

`opinion_classification.enabled = true` のときだけ実行されます。意見ごとに独立した yes/no ラベルをLLMで付けます。定義と注意点は [意見の分類ラベル](opinion-classification.md) を参照してください。

**出力1: `opinion_classifications.csv`**

| カラム名 | 型 | 説明 |
|---|---|---|
| `arg-id` | string | 意見ID |
| `hate_or_insult` | string | `yes` / `no`（侮辱・ヘイト表現） |
| `policy_proposal` | string | `yes` / `no`（政策・制度への提案） |

**出力2: `opinion_classification_summary.json`**

ラベルごとの件数と比率（分母は分類した意見数）、使用した provider / model、注意書き。

`hierarchical_aggregation` はこのCSVが存在すると、`hierarchical_result.json` の `arguments[].attributes` にラベル列を追加します（元コメントの `attribute_*` と同じ場所）。

---

### 2) `analysis.embedding`

**出力: `embeddings.pkl`**

- Pythonのpickle形式
- **list[dict]** として保存
- 各要素は `{ "arg-id": str, "embedding": numpy.ndarray }`（`embedding` は 1 次元・float32 の numpy 配列）

例（概念）:

```python
import numpy as np

[
  {"arg-id": "A1_0", "embedding": np.array([0.12, -0.01, ...], dtype=np.float32)},
  {"arg-id": "A2_0", "embedding": np.array([0.08, 0.03, ...], dtype=np.float32)},
]
```

古いレポートの `embeddings.pkl`（`--reuse-from`・複製・ストレージ同期で残ったもの）は、別の形式のことがあります。

- `embedding` が Python の `list[float]` の `list[dict]`
- `arg-id` を持たない `list[dict]`（行の順序で `args.csv` と対応）
- pandas DataFrame（`embedding` 列）。v2.0.0〜v4.0.0 が書いた形式で、読むには pandas が要ります（analysis-core と API の依存には入っていません）。analysis-core は、この形式の `embeddings.pkl` を読むステップ（クラスタリング・LLM grouping）を実行するときに、embedding ステップを再実行して今の形式で作り直します

読む側の注意:

- `list[dict]` の形式なら、`embedding` が ndarray でも list でも、`np.asarray([item["embedding"] for item in records], dtype=np.float32)` で同じ 2 次元配列にそろえられます
- `embedding` は list ではないので、`+` は連結ではなく要素ごとの和になります。`array_a == array_b` は要素ごとの真偽値の配列を返し、その結果をそのまま `if` の条件に使うと例外（`ValueError`）になります。配列全体が等しいかは `np.array_equal(array_a, array_b)` で比べてください
- JSON に書き出すときは `.tolist()` で list にしてください（ndarray のままでは `json.dumps` が `TypeError` になります）。float32 由来の誤差で、`0.1` が `0.10000000149011612` のように出ます

---

### 3) `analysis.hierarchical_clustering`

**出力: `hierarchical_clusters.csv`**

| カラム名 | 型 | 説明 |
|---|---|---|
| `arg-id` | string | 意見ID |
| `argument` | string | 意見本文 |
| `x` | float | UMAPでのX座標 |
| `y` | float | UMAPでのY座標 |
| `cluster-level-{n}-id` | string | 階層クラスタID（例: `1_3`） |

`cluster_nums` の設定に応じて `cluster-level-1-id`, `cluster-level-2-id` ... が増えます。

---

### 4) `analysis.hierarchical_initial_labelling`

**出力: `hierarchical_initial_labels.csv`**

`hierarchical_clusters.csv` に **最下層クラスタのラベル列**を追加したものです。

- 追加される列名は `cluster-level-{max}-label` / `cluster-level-{max}-description`
- `{max}` は最も細かいクラスタレベル

---

### 5) `analysis.hierarchical_merge_labelling`

**出力: `hierarchical_merge_labels.csv`**

クラスタを行形式に変換したラベル一覧です。

| カラム名 | 型 | 説明 |
|---|---|---|
| `level` | int | 階層レベル（1..） |
| `id` | string | クラスタID |
| `label` | string | ラベル |
| `description` | string | 説明文 |
| `value` | int | クラスタ内の意見数 |
| `parent` | string | 親クラスタID（level=1は `0`） |
| `density` | float | 密度スコア |
| `density_rank` | int | 密度順位 |
| `density_rank_percentile` | float | 密度の順位パーセンタイル |

---

### 6) `analysis.hierarchical_overview`

**出力: `hierarchical_overview.txt`**

- 全体概要のテキスト
- 現状は **level=1クラスタ**を対象に生成

---

### 7) `analysis.hierarchical_aggregation`

**出力: `hierarchical_result.json`**

主要フィールド：

- `arguments`: 意見一覧
- `clusters`: クラスタ一覧
- `comment_num`: 元コメント数
- `overview`: 概要文
- `propertyMap`: 属性マップ（必要な場合のみ）
- `translations`: 翻訳データ（存在する場合のみ）
- `config`: 実行時設定

`arguments` の構造（抜粋）:

```json
{
  "arg_id": "A1_0",
  "argument": "意見本文",
  "comment_id": "1",
  "x": 0.123,
  "y": -0.456,
  "p": 0,
  "cluster_ids": ["0", "1_3", "2_7"],
  "attributes": {"author": "山田太郎"},
  "url": "https://..."
}
```

`attributes` には、入力CSVの `attribute_*` 列に加えて、`opinion_classification` を有効にした場合はラベル列（`"hate_or_insult": "no"`, `"policy_proposal": "yes"`）が入ります。

`clusters` の構造（抜粋）:

```json
{
  "level": 1,
  "id": "1_3",
  "label": "交通",
  "takeaway": "交通に関する意見",
  "value": 42,
  "parent": "0",
  "density_rank_percentile": 0.83
}
```

> 注: `propertyMap` を使う場合は、`args.csv` に該当カラムが存在する必要があります。
> 存在しない場合は `hierarchical_aggregation` がエラーになります。

**追加出力（条件付き）: `final_result_with_comments.csv`**

`config.is_pubcom = true` の場合、以下のCSVが生成されます。

> 注: **このCSVのみ** `arg_id` / `category_id` のように snake_case に変換されます（他のCSVは基本的に `arg-id` などの kebab-case）。  
> 元データ（`args.csv`, `hierarchical_clusters.csv`）は kebab-case のままです。

| カラム名 | 説明 |
|---|---|
| `comment-id` | 元コメントID |
| `original-comment` | 元コメント本文 |
| `arg_id` | 意見ID |
| `argument` | 意見本文 |
| `category_id` | level=1クラスタID |
| `category` | level=1クラスタラベル |
| `source` / `url` | 入力CSVに存在する場合のみ追加 |
| `attribute_*` | 入力CSVに存在する属性カラム |

---

### 8) `analysis.hierarchical_visualization`

**出力: HTML / 静的レポート**

`REPORT={dataset} npm run build` により可視化レポートを生成します。
生成物の配置先は `report_dir` の設定に依存します（デフォルトは `../report`）。

---

## 関連ドキュメント

- `docs/development/plugin-guide.md`
- `docs/development/opinion-classification.md`
- `docs/user-guide/cli-quickstart.md`
