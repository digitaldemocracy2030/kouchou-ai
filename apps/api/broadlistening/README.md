## 概要

`broadlistening` 配下では、自然言語処理技術を用いてテキストデータの解析を行います。処理は`hierarchical_main.py`を起点に実行され、複数のステップから構成されるパイプラインとして実装されています。
hierarchical_main.py は、FastAPI のサーバーにおいてレポート作成のリクエストがあった際に実行されるように設計されています。

## 実行フロー

`hierarchical_main.py`は以下のステップを順番に実行します：

1. **extraction**: テキストから意見（引数）を抽出
2. **embedding**: 抽出した意見のベクトル埋め込みを生成
3. **hierarchical_clustering**: 意見の階層的クラスタリングを実行
4. **hierarchical_initial_labelling**: 各クラスタの初期ラベル付け
5. **hierarchical_merge_labelling**: 階層間のラベルのマージと調整
6. **hierarchical_overview**: クラスタの概要生成
7. **hierarchical_aggregation**: 結果の集約と JSON 形式での出力
8. **hierarchical_visualization**: 結果の可視化レポート生成

## 各ステップの詳細

### 1. extraction

**目的**: 入力テキスト（コメント）から意見（引数）を抽出します。

**処理内容**:

- 入力 CSV ファイルからコメントを読み込み
- OpenAI API を使用して各コメントから意見を抽出
- 抽出した意見を CSV ファイルに保存
- comment-id と arg-id の関係を CSV ファイルに保存

**出力**: `outputs/{dataset}/args.csv` `outputs/{dataset}/relations.csv`

### 2. embedding

**目的**: 抽出した意見のベクトル埋め込みを生成します。

**処理内容**:

- 抽出した意見を読み込み
- OpenAI Embeddings モデルを使用して意見のベクトル表現を生成
- 生成した埋め込みを Pickle ファイルに保存

**出力**: `outputs/{dataset}/embeddings.pkl`

### 3. hierarchical_clustering

**目的**: 意見の階層的クラスタリングを実行します。

**処理内容**:

- 埋め込みデータを読み込み
- UMAP を使用して次元削減
- K-means で初期クラスタリング
- 階層的クラスタリングで異なるレベルのクラスタを生成
- 各レベルのクラスタ情報を CSV ファイルに保存

**出力**: `outputs/{dataset}/hierarchical_clusters.csv`

### 4. hierarchical_initial_labelling

**目的**: 各クラスタの初期ラベル付けを行います。

**処理内容**:

- クラスタリング結果を読み込み
- 各クラスタから意見をサンプリング
- OpenAI API を使用してクラスタのラベルと説明を生成
- 生成したラベル情報を CSV ファイルに保存

**出力**: `outputs/{dataset}/hierarchical_initial_labels.csv`

### 5. hierarchical_merge_labelling

**目的**: 階層間のラベルのマージと調整を行います。

**処理内容**:

- 初期ラベル付け結果を読み込み
- 階層間の親子関係を構築
- 各クラスタレベル間でラベルをマージ・調整
- クラスタの密度を計算
- 結果を CSV ファイルに保存

**出力**: `outputs/{dataset}/hierarchical_merge_labels.csv`

### 6. hierarchical_overview

**目的**: クラスタの概要を生成します。

**処理内容**:

- マージラベル結果を読み込み
- 特定レベル（デフォルトはレベル 1）のクラスタ情報を取得
- OpenAI API を使用してクラスタの概要を生成
- 生成した概要をテキストファイルに保存

**出力**: `outputs/{dataset}/hierarchical_overview.txt`

### 7. hierarchical_aggregation

**目的**: 結果を集約し JSON 形式で出力します。

**処理内容**:

- 前ステップの結果を読み込み
- 意見データ、クラスタデータ、プロパティマップなどを構築
- カスタムイントロを生成
- すべての情報を JSON 形式で保存
- コメント原文つき意見データを CSV ファイルに保存（CSV出力モードのみ）

**出力**: `outputs/{dataset}/hierarchical_result.json`
`outputs/{dataset}/final_result_with_comments.csv`（CSV出力モードのみ）

## クレジット

本パイプラインは、[AI Objectives Institute](https://www.aiobjectivesinstitute.org/) が開発した [Talk to the City](https://github.com/AIObjectives/talk-to-the-city-reports)を参考に開発されており、ライセンスに基づいてソースコードを一部活用し、機能追加や改善を実施しています。ここに原作者の貢献に感謝の意を表します。
