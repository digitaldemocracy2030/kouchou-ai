# 意見の分類ラベル（侮辱・ヘイト表現 / 政策提案）

抽出した意見ごとに、LLMで独立した yes/no のラベルを付ける任意ステップ `opinion_classification` の説明です。「ヘイトスピーチの比率を出せるか」「政策に関する生産的な議論だけに絞ったマップを作れるか」という問いに、既存の属性フィルタの仕組みで答えるために追加しました。

意見を削除・書き換えることはありません。ラベルは情報を足すだけで、全件がそのまま残ります。

## 何をするか

1. `args.csv` の意見1件ごとにLLMへ問い合わせ、各ラベルに該当するかを `true` / `false` で受け取る。
2. `opinion_classifications.csv`（`arg-id` と、ラベルごとの `yes` / `no` 列）と、件数・比率をまとめた `opinion_classification_summary.json` を書く。
3. `opinion_classification.enabled` が `true` のとき、`hierarchical_aggregation` が `opinion_classifications.csv` を見つけると、`hierarchical_result.json` の `arguments[].attributes` にラベルを追加する。元コメントの `attribute_*` 列と同じ場所なので、公開ビューアの属性フィルタ（`AttributeFilterDialog`）でそのまま絞り込める。ビューア側の変更は不要。

ラベルはコメント単位ではなく **意見（argument）単位** です。1つのコメントから抽出された複数の意見がそれぞれ別のラベルを持ちます。

## ラベルの定義

定義の正本は `packages/analysis-core/src/analysis_core/steps/opinion_labels.py` の `DEFAULT_LABELS` で、プロンプトはここから組み立てます。比率は定義に対してのみ意味を持つので、数字を示すときは必ず定義を添えてください。

| ラベルID | 名称 | 該当 | 非該当 |
|---|---|---|---|
| `hate_or_insult` | 侮辱・ヘイト表現 | 特定の個人・集団への侮辱・罵倒・蔑称・人格否定、国籍・民族・出身地域・性別・年齢・宗教・障害などの属性を理由にした差別・排除・敵意、危害や不幸を望む表現 | 政策・行為・発言への強い批判や不信、辞任・逮捕・処罰・捜査の要求（侮辱表現を伴わない場合）、皮肉・不満・失望、事実の指摘 |
| `policy_proposal` | 政策・制度への提案 | 公共の政策・制度・法律・行政運営について、取るべき対応や方向性を具体的に述べているもの（新設・廃止・改革・運用変更の要求、特定の政策や法案への明示的な賛否を含む） | 人物や団体の評価・感想、事実の記述、質問、感情の表明、特定の人物の辞任・逮捕・処罰・起用など人事や個人への対応だけを求めるもの、番組・出演者・メディアへの要望、対象が特定できない漠然とした不満 |

ラベルは互いに独立です。両方に該当する意見（例: 属性を理由にした排除を制度として求めるもの）も、どちらにも該当しない意見もあります。「建設的な政策議論」に絞るときは `policy_proposal = yes` かつ `hate_or_insult = no` でフィルタしてください。

`hate_or_insult` は法的・学術的な「ヘイトスピーチ」の定義ではありません。侮辱表現と属性に基づく差別・排除をひとつにまとめた作業定義です。狭義のヘイトスピーチ（属性を理由にした差別・排除）だけを数えたい場合はラベルを分けて定義し直す必要があります。

## 有効化

既定では無効です。意見1件につきLLM呼び出しが1回増えるため、必要なときだけ有効にしてください。

```json
{
  "opinion_classification": {
    "enabled": true,
    "workers": 3
  }
}
```

| 項目 | 説明 |
|---|---|
| `enabled` | `true` で実行。`false`（既定）のときは実行計画で `run: false` になり、`--force` でも実行しません |
| `workers` | 並列リクエスト数（既定 1） |
| `model` | 省略時は全体の `model` |
| `prompt` | 省略時は `DEFAULT_LABELS` から組み立てた既定プロンプト。変更する場合は応答のJSONキーが `labels` と一致するようにしてください |
| `labels` | 応答に含まれるべきラベルIDの配列。省略時は `["hate_or_insult", "policy_proposal"]`。`prompt` とセットで変更します |
| `timeout_seconds` | 1リクエストのタイムアウト。省略時は `LLM_REQUEST_TIMEOUT_SECONDS` |

プロバイダは他のステップと同じ `provider` / `local_llm_address` / `user_api_key` を使います。OpenAI互換のローカルLLM（Ollama など）でも動きます。

## 出力

`outputs/{dataset}/opinion_classifications.csv`

| カラム名 | 説明 |
|---|---|
| `arg-id` | 意見ID |
| `hate_or_insult` | `yes` / `no` |
| `policy_proposal` | `yes` / `no` |

`outputs/{dataset}/opinion_classification_summary.json`

```json
{
  "total": 2914,
  "labels": {
    "hate_or_insult": {"count": 120, "ratio": 0.0412},
    "policy_proposal": {"count": 530, "ratio": 0.1819}
  },
  "provider": "local",
  "model": "...",
  "label_ids": ["hate_or_insult", "policy_proposal"],
  "note": "..."
}
```

`ratio` の分母は **分類した意見の件数**（= 抽出された意見の件数）です。元コメント数でも投稿者数でもありません。

## 失敗の扱い

応答がJSONでない、ラベルが欠けている、真偽値でない、通信に失敗した、といった場合は「どちらにも該当しない」と見なさず、ステップ全体を失敗させます（`ClassificationBatchError`）。失敗した意見の `arg-id` と例外の種類だけをログに出し、意見本文は出しません。部分的な出力ファイルは書きません。前回の実行で書いた `opinion_classifications.csv` / `opinion_classification_summary.json` はステップの開始時に削除するので、失敗したときに古いラベルが集計に混ざることもありません。`enabled: true` で有効にしたこのステップが失敗すると、パイプライン全体が失敗します（ラベルなしで完了扱いにはしません）。

`enabled` を `false` に戻した場合、出力ディレクトリに前回の `opinion_classifications.csv` が残っていても `hierarchical_aggregation` はラベルを付けません。

## 読み方の注意

- ラベルはLLMの判定で、人手による検証はしていません。定義の境界（強い批判と侮辱、人事要求と制度要求など）では判定が揺れます。公開する前に、少なくともサンプルを読んで定義と判定のずれを確認してください。
- 比率は「この定義にこのモデルがこの入力で該当と判定した割合」です。入力は世論の代表サンプルではなく、投稿者・チャンネル・時期の偏りをそのまま含みます。
- 比較するときは、同じ定義・同じプロンプト・同じモデルでそろえてください。モデルやプロンプトを変えた数字を並べて増減を論じないでください。
- クラスタのラベル（例:「侮辱的言説の集積」）とこのラベルは別の仕組みです。クラスタは意味の近さでまとまるため、侮辱表現を含まない意見も同じクラスタに入ります。両者の件数が一致しないのは正常です。
- `opinion_classifications.csv` を削除して `hierarchical_aggregation` を再実行すると、`hierarchical_result.json` からラベルが消えます。
