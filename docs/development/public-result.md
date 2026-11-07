# 公開用レポート結果（public_result.json）

分析の出力ディレクトリ（`outputs/<dataset>/`）には、結果の JSON が 2 つ並びます。

| ファイル | 役割 | 誰が読むか | 契約 |
|---|---|---|---|
| `hierarchical_result.json` | **分析の全部入り**。設定（`config`）を含めて再分析・複製・管理画面の編集に必要なものを持つ | analysis-core の後続ステップ、API の複製・再実行、管理画面 | 内部形式。公開契約ではない |
| `public_result.json` | **公開用**。`hierarchical_result.json` から公開してよい項目だけを **ホワイトリスト** で写したもの | 公開 API、静的書き出し、公開ビューア、外部ツール | **公開契約**（このページ） |

公開 API・静的書き出し・ビューア・外部のツールが依存してよいのは `public_result.json` です。`hierarchical_result.json` の形は、再分析や管理機能の都合で変わることがあります。

## なぜ分けるか

`hierarchical_result.json` は分析・表示・説明のすべてを 1 ファイルで背負ってきました。集計ステップが設定を丸ごと書き出し、公開 API と静的書き出しがそのファイルをそのまま配布するため、設定に秘密が入ると公開ページに出ます。管理画面で入力した API キーの漏洩（[GHSA-xr6j-6w48-xh62](../self-hosting/security/user-api-key-leak-2026-10.md)）はこの構造で起きました。

修正後の集計は非公開のキーを **ブラックリスト** で除いています（`_public_config`）。ただし新しいステップや設定項目が増えると、明示的に除かない限りそのまま公開側に出ます。`public_result.json` は逆向きで、**ここに書いたキーしか含めません**。新しい項目を公開したいときは `analysis_core/public_result.py` とこのページの両方を更新します。

同じ理由で、意見ごとに属性を足すステップ（意見の分類ラベル、賛否・新規性スコアなど）は `arguments[].attributes` に書きます。`attributes` の中身はホワイトリストの対象外（自由形式）なので、属性を増やすたびに契約を変える必要はありません。

## いつ作られるか

`public_result.json` は `hierarchical_result.json` を書く（作り直す）たびに、同じ内容から作り直されます。`analysis_core.public_result.write_result_files()` が両方を一時ファイルに書いてから差し替えます。

- 集計ステップ（`analysis.hierarchical_aggregation`）
- レイアウト生成ステップ（`analysis.hierarchical_layout_generation`。`layouts` を書き足す）
- 翻訳 CLI（`kouchou-translate --result ...` で結果ファイルを上書きするとき）

管理画面でのラベル編集や再実行は集計をやり直すので、そこでも作り直されます。

古いレポート（この仕組みより前に作られたもの）には `public_result.json` がありません。パイプラインは「集計の出力が欠けている」と判定して次の実行時に集計をやり直し、ファイルを作ります。読む側で必要なら `build_public_result(hierarchical_result)` で同じ内容をその場で作れます。

## 公開 API が返すもの

公開 API の `GET /reports/{slug}` は、この契約の形を返します。

1. `hierarchical_result.json` があれば、そこから `build_public_result()` で毎回作る（`public_result.json` の無い古いレポートもこの経路）
2. `hierarchical_result.json` が無く `public_result.json` だけを置いた配信では、それを読む。壊れている・契約を満たさないときは作り直す元が無いので 500 を返す
3. 返す前に、レポートの公開範囲 `visibility` と、可視化設定があれば `visualizationConfig` を足す

結果ファイルがあるときに `public_result.json` を読まないのは、両者が食い違っていないことを確かめる手段が無いためです。2 つは同時に書かれますが、ストレージからファイル単位で復元・同期されると、古い写しの方が新しい更新日時を持つことがあります。正本から作れば、たとえば後から `hidden_properties` に足した属性の列が古い写しから漏れることはありません。読む量は従来（結果ファイルをそのまま返していたとき）と同じです。

どちらの経路でも、ホワイトリストにない項目（再分析用の設定、実行状態、`hidden_properties` に指定した属性の列など）は返しません。公開ビューアと静的書き出し（ビルド時に公開 API から取得する）はこの応答を読みます。管理画面の JSON ダウンロード（`/admin/reports/{slug}/json`）は従来どおり `hierarchical_result.json` を返します。

## 形（schema_version 1）

```json
{
  "schema_version": 1,
  "arguments": [ { "arg_id": "A1_0", "argument": "…", "comment_id": "c1", "x": 0.1, "y": 0.2, "p": 0,
                   "cluster_ids": ["0", "1_0", "2_3"], "attributes": { "age": "20代" }, "url": "https://…" } ],
  "clusters":  [ { "level": 1, "id": "1_0", "label": "…", "takeaway": "…", "value": 120, "parent": "0",
                   "density_rank_percentile": 0.2 } ],
  "comments":  { "c1": { "comment": "元コメント本文" } },
  "propertyMap": { "age": { "A1_0": "20代" } },
  "translations": { "en": { "overview": "…", "question": "…", "intro": "…", "clusters": { "1_0": { "label": "…", "takeaway": "…" } } } },
  "overview": "…",
  "comment_num": 1234,
  "config": { "...": "下の表" },
  "layouts": { "embedding_umap": { "kind": "point_layout", "points": { "A1_0": { "x": 0.1, "y": 0.2 } }, "meta": {} } },
  "default_layout_id": "embedding_umap"
}
```

| キー | 型 | 説明 |
|---|---|---|
| `schema_version` | int | この契約の版。互換性を壊す変更のときだけ上がる |
| `arguments[]` | object | 意見。`arg_id` / `argument` / `comment_id` / `x` / `y` / `p` / `cluster_ids` / `attributes` / `url` のみ。`attributes` は自由形式（元データの `attribute_*` 列と、意見ごとの分類・スコア） |
| `clusters[]` | object | クラスタ。`level` / `id` / `label` / `takeaway` / `value` / `parent` / `density_rank_percentile` のみ |
| `comments` | object | `comment_id` → `{ "comment": 本文 }`。レポート作成者が元コメントの公開を有効にした（`config.enable_original_comments`）ときだけ中身が入り、それ以外は `{}` |
| `propertyMap` | object | 属性名 → （`arg_id` → 値）。`hierarchical_aggregation.hidden_properties` に指定した属性は列ごと含めない |
| `translations` | object | 言語コード → 訳。各言語の `overview` / `question` / `intro` / `clusters` / `arguments` は省略可能。生成に使ったモデル等の `meta` は含めない |
| `overview` | string | 全体概要 |
| `comment_num` | int | 入力コメント数 |
| `config` | object | 表示に使う設定だけ（下の表） |
| `layouts` | object | 省略可能。レイアウト名 → `{ kind, points, meta }`。レイアウト生成ステップを実行したときだけ |
| `default_layout_id` | string | 省略可能。`layouts` の既定 |

### `config` に入るもの

公開ビューアが「問い・イントロ・使ったモデル・分析手順」の表示に使う項目だけです。

| キー | 用途 |
|---|---|
| `question`, `intro` | レポートの問いと、件数・モデルを添えた説明文 |
| `model`, `provider`, `is_embedded_at_local`, `analysis_mode` | モデル名の表示、レイアウトの既定 |
| `enable_source_link`, `enable_original_comments` | 出典リンク・元コメント表示の有無 |
| `plan[]` | 各ステップの `step` / `run` / `reason` |
| `extraction` | `workers` / `limit` / `properties` / `categories` / `category_batch_size` / `source_code` / `prompt` / `model` |
| `embedding` | `model` / `source_code` |
| `hierarchical_clustering` | `cluster_nums` / `source_code` |
| `hierarchical_initial_labelling`, `hierarchical_merge_labelling` | `workers` / `source_code` / `prompt` / `model` |
| `hierarchical_overview` | `source_code` / `prompt` / `model` |
| `hierarchical_aggregation`, `hierarchical_visualization` | `source_code` のみ |
| `opinion_classification` | `enabled` / `labels` |

### 入れないもの

- 秘密と内部情報：`user_api_key`、`_` 始まりのランタイムキー（サーバー内部パス）、`local_llm_address`、タイムアウト等の実行環境
- 実行状態：`status` / `start_time` / `completed_jobs` / `lock_until` / `current_job` / `current_job_started` / `previous`（これらは `hierarchical_status.json` の領分。古いレポートの `config` には混ざっていることがある）
- 内部の識別子：`name` / `input` / `output_dir`
- 「何を隠したか」と隠した属性の値：`hierarchical_aggregation.hidden_properties` の中身（どの属性のどの値を隠す設定にしたか）と、指定した属性の列そのもの。
  集計はこの設定に当たるコメントの元コメント本文を `comments` から除くが、`hierarchical_result.json` の `propertyMap` には指定した属性の値を意見ごとに書いている。`public_result.json` ではその属性を `propertyMap` から列ごと外す。なお、当たるコメントから抽出した意見（`arguments`）は現状どおり残る。この設定を「本文だけを隠す」ものとするか「その値を持つコメント由来の意見ごと隠す」ものとするかは [#1180](https://github.com/digitaldemocracy2030/kouchou-ai/issues/1180) で扱う
- 表示に使っていないもの：`hierarchical_visualization.replacements`、翻訳の `meta`

## 互換性の扱い

- **省略可能なキーを足す**のは互換な変更で、`schema_version` は上げません。読む側は知らないキーを無視してください
- **キーを消す・意味や型を変える**ときは `schema_version` を上げ、読む側（公開 API、ビューア、静的書き出し）を同時に更新します
- `arguments[].attributes` の中身はこの契約の対象外です。属性を足すステップは自由に増やせます
- 公開 API は配信時に `visibility`（公開範囲）を付けます。可視化設定（`visualization_config.json`）は別ファイルで、この artifact には含みません

## 検査

`apps/api/scripts/check_report_secret_leak.py --report-dir <dir>` は `hierarchical_result.json` と並んで `public_result.json` も秘密の混入を確認します。`scrub_report_secrets.py` は既存レポートの両方から非公開キーを取り除きます。

## 今後

この仕組みは段階的に入れています（Issue [#1178](https://github.com/digitaldemocracy2030/kouchou-ai/issues/1178)）。

1. **書く**（済み）：集計・レイアウト生成・翻訳が `public_result.json` を書く。契約を宣言する
2. **読む**（済み）：公開 API が契約の形（`build_public_result()` の出力）を返し、ビューアの型を契約に合わせる。結果ファイルがあればそこから作り、`public_result.json` だけの配信ではそれを読む
3. **分ける**：意見全件を 1 回で画面に渡す経路を分割読み込みにし、静的書き出しでも HTML の隣に JSON を置く

`hierarchical_result.json` の各項目の説明は [プラグイン出力データ構造](plugin-output-data-structures.md) を参照してください。
