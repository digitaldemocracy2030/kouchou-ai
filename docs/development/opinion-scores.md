# 意見ごとのスコア（賛否スコア / 新規性スコア）

抽出した意見 1 件ごとに数値の属性を付ける任意ステップ 2 つの説明です。どちらも既定では無効で、[意見の分類ラベル](opinion-classification.md)（`opinion_classification`）と同じ型の「意見ごとに属性を足す」ステップです。

| ステップ | 付ける属性 | 値 | LLM | 実行位置 |
|---|---|---|---|---|
| `opinion_stance` | `stance_score` | -1.0（反対）〜 +1.0（賛成）。判定不能は属性なし | 使う（意見 1 件につき 1 回） | `extraction` の後 |
| `opinion_novelty` | `novelty_score` | 0.0〜1.0（高いほど他の意見から遠い） | 使わない | `embedding` の後 |

意見を削除・書き換えることはありません。スコアは情報を足すだけで、全件がそのまま残ります。

## なぜ属性として付けるか

同じトピックに賛成と反対の意見が混ざったクラスタは、ラベルを読んでも洞察になりません（書籍『ブロードリスニング』13.4.3 のセンチメント次元の問題意識）。埋め込みやクラスタリングを変える前に、まず意見ごとの属性として賛否を持てば、公開ビューアの属性フィルタ（数値属性の範囲指定）で「賛成だけの地図」「反対だけの地図」を今の散布図のまま見られます。ビューア側の変更は要りません。

新規性スコアは、埋め込み空間で他の意見から遠い意見（少数で珍しい意見）の候補に印を付けます。「珍しい」と「重要」は別で、何を重要と見るかは分析者が決めます。スコアは候補を絞るだけです。

## 賛否スコア `opinion_stance`

### 何をするか

1. `args.csv` の意見 1 件ごとに、「対象」と「意見」を LLM へ渡し、`applicable`（対象への賛否を読み取れるか）と `stance_score`（-1.0〜+1.0）を受け取る。
2. `opinion_stances.csv`（`arg-id`, `stance_score`。判定不能は空欄）と `opinion_stance_summary.json`（件数・平均・5 区間の分布・対象）を書く。
3. `opinion_stance.enabled` が `true` のとき、`hierarchical_aggregation` が `hierarchical_result.json` の `arguments[].attributes.stance_score` に **数値** で入れる。判定不能の意見には入れない（0.0 にはしない）。

「対象」は `opinion_stance.target` で指定します。省略時はレポートの `question` を対象にします。パブコメなら「この案に賛成か」、特定の施策への賛否を見たいなら `target` にその施策を書きます。

### 有効化

```json
{
  "question": "市内に新しい図書館を建設する計画について",
  "opinion_stance": {
    "enabled": true,
    "workers": 3
  }
}
```

| 項目 | 説明 |
|---|---|
| `enabled` | `true` で実行。`false`（既定）のときは実行計画で `run: false` になり、`--force` でも実行しません |
| `workers` | 並列リクエスト数（既定 1） |
| `target` | 賛否の対象。省略時は `question`。`question` を変えると（`target` 省略時は）このステップも再実行されます |
| `model` | 省略時は全体の `model` |
| `prompt` | 省略時は既定プロンプト。変更する場合は応答の JSON が `applicable` と `stance_score` の 2 キーになるようにしてください |
| `timeout_seconds` | 1 リクエストのタイムアウト。省略時は `LLM_REQUEST_TIMEOUT_SECONDS` |

### 出力

`outputs/{dataset}/opinion_stances.csv`

| カラム名 | 説明 |
|---|---|
| `arg-id` | 意見ID |
| `stance_score` | -1.0〜+1.0 の数値。判定不能は空欄 |

`outputs/{dataset}/opinion_stance_summary.json`

```json
{
  "total": 997,
  "scored": 940,
  "not_applicable": 57,
  "mean": 0.12,
  "distribution": {"strongly_against": 180, "against": 90, "neutral": 220, "for": 150, "strongly_for": 300},
  "provider": "openai",
  "model": "...",
  "target": "市内に新しい図書館を建設する計画について",
  "note": "..."
}
```

分布の区間は `<= -0.6` / `< -0.2` / `<= 0.2` / `< 0.6` / それ以上です。

### 失敗の扱い

応答が JSON でない、キーが欠けている、`stance_score` が数値でない・範囲外、通信に失敗した、といった場合は「中立」と見なさず、ステップ全体を失敗させます（`StanceBatchError`）。失敗した意見の `arg-id` と例外の種類だけをログに出し、意見本文や API キーは出しません。部分的な出力ファイルは書きません。前回の `opinion_stances.csv` / `opinion_stance_summary.json` はステップの開始時に削除します。`enabled: true` で有効にしたこのステップが失敗すると、パイプライン全体が失敗します。

## 新規性スコア `opinion_novelty`

### 何をするか

1. `embeddings.pkl` を読み、意見ごとに「他の意見からの遠さ」を計算する。
2. 遠さの順位を 0.0〜1.0 に正規化して `opinion_novelty.csv`（`arg-id`, `novelty_score`）に書く。計算方法とパラメータは `opinion_novelty_summary.json` に残す。
3. `opinion_novelty.enabled` が `true` のとき、`hierarchical_aggregation` が `arguments[].attributes.novelty_score` に数値で入れる。

LLM は呼びません。`clustering` の追加依存（scikit-learn）を使います。

### 計算方法

| `method` | 内容 | パラメータ |
|---|---|---|
| `knn_distance`（既定） | 自分を除く k 近傍までの平均コサイン距離。説明しやすく、パラメータが `k` だけ | `k`（既定 10。件数 - 1 を上限に丸める） |
| `isolation_forest` | Isolation Forest の異常度（tokoroten/farbrain と同じ方式） | `seed`（既定 42） |

どちらも生の値ではなく **順位**（同値は平均順位）を 0.0〜1.0 にしたものを書きます。値そのものに意味はなく、「上位 10%」のような相対的な絞り込みに使ってください。意見が 1 件なら 0.0 です。

### 有効化

```json
{
  "opinion_novelty": {
    "enabled": true,
    "method": "knn_distance",
    "k": 10
  }
}
```

### 出力

`outputs/{dataset}/opinion_novelty.csv`（`arg-id`, `novelty_score`）と `outputs/{dataset}/opinion_novelty_summary.json`:

```json
{
  "total": 997,
  "method": "knn_distance",
  "params": {"k": 10},
  "raw_value": {"description": "k 近傍までの平均コサイン距離", "min": 0.094, "max": 0.617, "mean": 0.319},
  "note": "..."
}
```

## 公開ビューアでの使い方

どちらの属性も数値なので、属性フィルタのダイアログで範囲を指定して絞り込めます。

- 「賛成の意見だけ」: `stance_score` を `0.2`〜`1.0`
- 「反対の意見だけ」: `stance_score` を `-1.0`〜`-0.2`
- 「珍しい意見の候補」: `novelty_score` を `0.9`〜`1.0`

判定不能（`applicable: false`）の意見には `stance_score` が無いので、範囲フィルタでは「属性なし」として扱われます。

## 読み方の注意

- 賛否スコアは LLM の判定で、人手による検証はしていません。対象の書き方で結果が変わるので、公開する前に少なくともサンプルを読んで、対象とスコアの向きが合っているか確認してください。
- 賛否の平均や分布は「この対象にこのモデルがこの入力で付けた値」です。入力は世論の代表サンプルではなく、投稿者・チャンネル・時期の偏りをそのまま含みます。
- 新規性スコアは埋め込みモデルと意見の件数に依存します。別のレポートの値と比べないでください。同じ内容の意見が多いほどその意見のスコアは下がります（珍しくない）。
- クラスタのラベルとこれらのスコアは別の仕組みです。同じクラスタに賛成と反対が混ざるのは正常で、それを見分けるためのスコアです。
- `opinion_stances.csv` / `opinion_novelty.csv` を削除して `hierarchical_aggregation` を再実行すると、`hierarchical_result.json` からスコアが消えます。`enabled` を `false` に戻した場合、ファイルが残っていてもスコアは付きません。
