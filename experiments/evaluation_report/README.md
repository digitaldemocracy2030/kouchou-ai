# クラスタリング評価レポート生成ツール

このツールは、クラスタリング結果に対して定量評価（シルエットスコア）および定性評価（LLMを用いた評価）を実施し、CSVおよびHTML形式でレポートを出力するものです。

## 主な特徴

- **LLMを活用した4指標の自動評価**  
  明確さ（Clarity）、一貫性（Coherence）、整合性（Consistency）、差異性（Distinctiveness）

- **まとまり具合（シルエットスコア）に基づく分離評価**  
  シルエットスコア（「クラスタ内の平均距離」と「最も近い別クラスタとの距離」）および1〜5段階スコアで定量的に評価

- **レポート出力**  
  クラスタ単位・意見単位のCSV、Webブラウザ閲覧可能なHTMLレポート

## クイックスタート（同梱サンプルで再現）

第三者が追加データの取得なしに動作確認できるよう、小さな**合成**サンプルデータセットを
`inputs/sample/` に同梱しています（実在する意見・個人情報は含みません）。

silhouette（まとまり具合）評価は **LLM / OpenAI API を一切使わずに** 回せます。

```bash
# 1. 依存をインストール（silhouette 経路だけなら軽量な4つで足りる）
pip install numpy pandas scikit-learn jinja2
#   full 経路（LLM評価）も使うなら:
#   pip install -r requirements.txt

# 2. silhouette のみで一括実行（APIキー不要・課金なし）
python src/run_evaluation.py sample --skip-llm
```

出力は `outputs/sample/` に生成されます（本リポジトリにも出力例を同梱済み）。

- `cluster_evaluation.csv` … クラスタ単位の評価（LLM列は `--skip-llm` 時は空）
- `comment_evaluation.csv` … 意見（コメント）単位の silhouette 指標
- `report.html` … ブラウザで開けるHTMLレポート

サンプルデータは決定論的に再生成できます（乱数シード固定）:

```bash
python make_sample_dataset.py          # inputs/sample/ を作り直す
```

### 2つの実行経路

| 経路 | コマンド | 必要なもの | 得られる指標 |
| --- | --- | --- | --- |
| **silhouette のみ（最小）** | `python src/run_evaluation.py <dataset> --skip-llm` | numpy / pandas / scikit-learn / jinja2 のみ。API不要・課金なし | silhouette, centroid, nearest（1〜5段階含む） |
| **full（LLM-judge 込み）** | `python src/run_evaluation.py <dataset>` | 上記 + OpenAI APIキー（`OPENAI_API_KEY`）、`analysis-core`、課金あり | 上記 + clarity / coherence / consistency / distinctiveness |

> LLM-judge は OpenAI API 課金を伴うため、本リポジトリでは実行結果を同梱していません。
> `--mode print` を使うと API を呼ばずに評価用プロンプトだけを出力でき、ChatGPT 等に貼り付けて
> 手動評価 → `inputs/{dataset}/evaluation_consistency_llm_level{1,2}.json` に保存することで
> CSV / HTML に反映できます（詳細は末尾「備考」参照）。

## 入力データの形式

`inputs/{dataset}/` には、クラスタリング pipeline
（`packages/analysis-core`）の出力ファイルを置きます。silhouette (umap) 経路で必要なのは
以下の4ファイルです（`embeddings.pkl` は `--source embedding` を使う時だけ必要）。

| ファイル | 主なカラム / キー | 使う処理 |
| --- | --- | --- |
| `hierarchical_clusters.csv` | `arg-id`, `argument`, `x`, `y`, `cluster-level-1-id`, `cluster-level-2-id` | silhouette 計算 |
| `hierarchical_merge_labels.csv` | `level`, `id`, `label`, `description`, `value`, `parent`, `density*` | クラスタCSV |
| `hierarchical_result.json` | `arguments[]`, `clusters[]`, `config.question`, `overview` | 意見CSV / HTML |
| `args.csv` | `arg-id`, `argument` | LLM評価（full 経路） |

同梱サンプルの生成ロジックは `make_sample_dataset.py` を参照してください（各ファイルの
正確なスキーマがコードで読めます）。

## ディレクトリ構成

```
project-root/
├── make_sample_dataset.py  ... 同梱サンプル（合成データ）の生成スクリプト
├── inputs/
│   ├── sample/         ... 同梱の合成サンプル（args.csv, hierarchical_*.csv/json）
│   └── {dataset-id}/   ... 入力元データ（args.csv, clusters.csv,中間データJSON 等）
├── outputs/
│   ├── sample/         ... サンプルの出力例（CSV, HTML）
│   └── {dataset-id}/   ... 評価出力ファイル群（CSV,  HTML）
├── src/
│   └── run_evaluation.py   ... 一括実行スクリプト（--skip-llm で silhouette のみ）
```


## 使用方法

### 1. データの取得（例：Docker 環境から）

```bash
docker cp kouchou-ai-api-1:/app/broadlistening/pipeline/outputs/5c783025-ab42-4676-b68b-7e1fe9858c05 ./inputs/
```

この場合、`5c783025-ab42-4676-b68b-7e1fe9858c05` がデータセットIDになります。

### 2. 評価の実行

```bash
python src/run_evaluation.py 5c783025-ab42-4676-b68b-7e1fe9858c05
```

### 3. オプション引数（必要に応じて）

| 引数              | 内容                           | 例                   |
| --------------- | ---------------------------- | ------------------- |
| `--level`       | 評価対象のクラスタ階層レベル（1 または 2）      | `--level 2`         |
| `--max-samples` | LLMプロンプトに含める最大意見数            | `--max-samples 500` |
| `--mode`        | `api` または `print`（プロンプト出力のみ） | `--mode print`      |
| `--model`       | 使用するOpenAIモデル名               | `--model gpt-4o-mini`    |
| `--skip-llm`    | LLM評価をスキップし silhouette のみ実行（API不要） | `--skip-llm`       |


## クラスタリング評価結果の出力ファイルについて

このディレクトリには、クラスタリング評価の実行結果として以下のファイルが出力されます。

## 出力ファイル一覧

### 1. `cluster_evaluation.csv`

クラスタ単位での評価結果がまとめられたCSVファイルです。各クラスタごとに以下の評価項目が含まれます：

| 項目名 | 内容 |
|--------|------|
| `clarity` | 明確さ：主語・述語の明瞭さや、意図の伝わりやすさ |
| `coherence` | 一貫性：説明の論理的な流れや構成のつながり |
| `consistency` | 意見の整合性：意見とその説明の論理的一貫性 |
| `distinctiveness` | 他クラスタとの差異：意見内容が他クラスタとどれだけ異なるか |
| `llm_comment` | 評価の根拠や特徴をまとめたコメント（LLMによる出力） |
| `silhouette` | クラスタのまとまり具合を示す シルエットスコア（–1〜+1） |
| `silhouette_score` | 上記スコアを5段階に正規化したもの（1〜5） |
| `centroid_dist` | 同一クラスタ内の意見間の平均距離（中心との近さ） |
| `centroid_score` | 上記スコアを5段階に正規化したもの（1〜5） |
| `nearest_dist` | 最も近い別クラスタまでの距離（他クラスタとの距離） |
| `nearest_score` | 上記スコアを5段階に正規化したもの（1〜5） |

### 2. `comment_evaluation.csv`

`cluster_evaluation.csv` と同様の構成ですが、各「意見（コメント）」単位での評価を行った場合に出力されます。評価関連の列の意味は共通です。

---

## 🌐 3. `report.html`

評価結果をグラフィカルにまとめたHTMLレポートです。

- 各クラスタの評価指標のスコアとコメントを、視覚的に整理しています。
- ユーザーやステークホルダーがWebブラウザ上で直感的に確認できます。

## 備考

* OpenAI APIキーは環境変数などで設定しておく必要があります。
* 入力データ形式は `args.csv`, `embeddings.pkl`,`hierarchical_clusters.csv`, `hierarchical_merge_labels.csv` が前提です。
* `print` モードではAPIを使わず、LLMに貼り付け可能なプロンプトを標準出力に出力します。  
  `--mode print` を指定すると、LLM評価は自動実行されず、ChatGPTなどで利用可能な評価用プロンプトが出力されます。

このモードは以下の用途に便利です：

- ChatGPTのWeb版や任意のLLMツールにコピペして手動で評価を行いたい場合  
- プロンプト内容を微調整・確認したい場合（例：評価基準の修正、説明追加など）  
- OpenAI APIを使わず、無料枠や外部ツールで評価したい場合  

出力されたプロンプトは `outputs/{dataset}/prompt_level{1 or 2}.txt` に保存され、内容は標準出力にも表示されます。  
ChatGPTで得た評価結果を `inputs/{dataset}/evaluation_consistency_llm_level{1 or 2}.json` に保存すれば、  
オプションなしで再度実行することで CSV出力やHTMLレポートに反映されます。