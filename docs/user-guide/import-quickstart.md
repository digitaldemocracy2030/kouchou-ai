# Python スクリプトからの利用ガイド

このガイドでは、`kouchou-ai-analysis-core` パッケージを Python スクリプトから import して利用する方法を説明します。

## 前提条件

- Python 3.12 以上
- OpenAI API キー

## 1. インストール

```bash
pip install 'kouchou-ai-analysis-core[embeddings,clustering]'
```

軽量な base install (`pip install kouchou-ai-analysis-core`) でも top-level import は可能ですが、local embedding や hierarchical clustering を使うには optional extras が必要です。

## 2. 基本的な使い方

### PipelineOrchestrator を使用する

```python
import os
from pathlib import Path
from analysis_core import PipelineOrchestrator

# 環境変数の設定
os.environ["OPENAI_API_KEY"] = "sk-your-api-key"

# 設定辞書を作成
config = {
    "name": "市民意見分析",
    "question": "市民からどのような意見が寄せられていますか？",
    "input": "my-comments",  # inputs/my-comments.csv
    "model": "gpt-4o-mini",
    "provider": "openai",
    "is_embedded_at_local": False,
    "extraction": {
        "workers": 3,
        "limit": 100,
    },
}

# パイプラインを実行
orchestrator = PipelineOrchestrator.from_dict(
    config=config,
    output_dir="my-analysis",
    input_base_dir=Path("./inputs"),
    output_base_dir=Path("./outputs"),
)

result = orchestrator.run_default()

print(f"成功: {result.success}")
print(f"出力ディレクトリ: {result.output_dir}")
```

`hierarchical_clustering.cluster_nums` は省略可能です。省略した場合は、extraction 後の argument 数に基づいておすすめ値が自動計算されます。

### PipelineConfig クラスを使用する

設定の検証やJSONファイルからの読み込みには `PipelineConfig` を使用します。

```python
from analysis_core import PipelineConfig, PipelineOrchestrator

# JSONファイルから読み込み
config = PipelineConfig.from_json("config.json")

# 辞書に変換してオーケストレータに渡す
orchestrator = PipelineOrchestrator.from_dict(config.to_dict())
result = orchestrator.run_default()
```

## 3. 個別ステップの実行

特定のステップだけを実行するには、`PipelineOrchestrator.from_config()` に `only` を渡します（CLI の `--only` と同じ動きです）。

`analysis_core.steps` の各ステップ関数（`extraction` など）は、パイプラインが補った設定（出力先・入力先・既定のプロンプトなど）が入った config を前提にしています。手で書いた config を渡して直接呼び出すと動かないため、オーケストレータ経由で実行してください。

### 抽出のみを実行

設定ファイル `my-analysis.json` を用意します。出力先は設定ファイル名から決まり、この例では `outputs/my-analysis/` になります。

```json
{
  "name": "市民意見分析",
  "question": "市民からどのような意見が寄せられていますか？",
  "input": "my-comments",
  "model": "gpt-4o-mini",
  "provider": "openai",
  "is_embedded_at_local": false,
  "extraction": {
    "workers": 1,
    "limit": 10
  }
}
```

```python
from pathlib import Path
from analysis_core import PipelineOrchestrator

orchestrator = PipelineOrchestrator.from_config(
    "my-analysis.json",
    only="extraction",
    input_base_dir=Path("./inputs"),
    output_base_dir=Path("./outputs"),
)
result = orchestrator.run_default()
print(f"成功: {result.success}")
```

`only` には `extraction`、`embedding`、`hierarchical_clustering`、`hierarchical_initial_labelling`、`hierarchical_merge_labelling`、`hierarchical_overview`、`hierarchical_aggregation` などのステップ名を指定できます。2 つ目以降のステップは、前のステップの出力（`args.csv` など）が出力先に揃っている必要があります。たとえば `only="hierarchical_aggregation"` とすると、LLM を呼ばずに `hierarchical_result.json` だけを作り直せます。

## 4. 結果の読み込みと利用

`hierarchical_result.json` の主な項目は次のとおりです。

| 項目 | 内容 |
|------|------|
| `comment_num` | 入力コメント数 |
| `overview` | AI が生成した全体の要約 |
| `arguments` | 抽出された意見のリスト。各要素に `arg_id`・`argument`（意見本文）・`comment_id`（元コメントの ID）・`x` / `y`（散布図の座標）・`cluster_ids`（所属クラスタの ID）などが入ります |
| `clusters` | クラスタのリスト。各要素に `level`（`0` は全体、`1` 以降が各階層）・`id`・`label`・`takeaway`（説明）・`value`（意見数）・`parent`（親クラスタの ID）などが入ります |
| `comments` | 現在は常に空です。元のコメント本文は入力 CSV から読み込んでください |

### 結果JSONの読み込み

```python
import json
from pathlib import Path

result_path = Path("outputs/my-analysis/hierarchical_result.json")
with open(result_path, encoding="utf-8") as f:
    data = json.load(f)

# 基本情報
print(f"コメント数: {data['comment_num']}")
print(f"意見数: {len(data['arguments'])}")
print(f"要約: {data['overview']}")

# クラスター情報（第1階層と、その下の第2階層。意見数は value に入っている）
clusters = data['clusters']
for parent in [c for c in clusters if c['level'] == 1]:
    print(f"[{parent['label']}] ({parent['value']}件)")
    for child in [c for c in clusters if c['parent'] == parent['id']]:
        print(f"  [{child['label']}] ({child['value']}件)")
```

### 意見データの取得

```python
import csv

# 抽出された意見（リスト）
for arg in data['arguments'][:5]:
    print(f"{arg['arg_id']}: {arg['argument']}")

# 元のコメント本文は結果JSONに入っていないため、入力CSVから comment_id で引く
with open("inputs/my-comments.csv", encoding="utf-8-sig") as f:
    comments = {row['comment-id']: row['comment-body'] for row in csv.DictReader(f)}

for arg in data['arguments'][:5]:
    print(f"{arg['comment_id']}: {comments[arg['comment_id']][:50]}...")
```

### 埋め込みベクトルの読み込み

`embeddings.pkl` には、意見ごとに `arg-id` と `embedding` を持つ辞書のリストが保存されています。

```python
import pickle
import numpy as np

with open("outputs/my-analysis/embeddings.pkl", "rb") as f:
    records = pickle.load(f)

arg_ids = [r['arg-id'] for r in records]
vectors = np.array([r['embedding'] for r in records])
print(vectors.shape)  # (意見数, 埋め込みの次元数)
```

## 5. Pandas での分析

```python
import pandas as pd
import json

with open("outputs/my-analysis/hierarchical_result.json", encoding="utf-8") as f:
    data = json.load(f)

# 意見をDataFrameに変換
df_args = pd.DataFrame(data['arguments'])

print(df_args[['arg_id', 'argument', 'comment_id']].head())
print(f"\n意見数: {len(df_args)}")

# 第1階層のクラスター別の集計
# cluster_ids は ['0', '1_3', '2_7'] のような形で、先頭の '0' は全体、2 番目が第1階層のクラスタ ID
df_args['cluster_level1'] = df_args['cluster_ids'].str[1]
labels = {c['id']: c['label'] for c in data['clusters']}
counts = df_args.groupby('cluster_level1').size().rename(index=labels)
print(counts.sort_values(ascending=False))
```

## 6. Matplotlib での可視化

### クラスター別意見数の棒グラフ

```python
import json
import matplotlib.pyplot as plt

# 日本語フォントの設定（環境に応じて変更）
plt.rcParams['font.family'] = 'Hiragino Sans'

with open("outputs/my-analysis/hierarchical_result.json", encoding="utf-8") as f:
    data = json.load(f)

# レベル1のクラスターを取得（意見数は value に入っている）
clusters = [c for c in data['clusters'] if c['level'] == 1]
labels = [c['label'][:15] + '...' if len(c['label']) > 15 else c['label']
          for c in clusters]
counts = [c['value'] for c in clusters]

plt.figure(figsize=(10, 6))
plt.barh(labels, counts, color='steelblue')
plt.xlabel('意見数')
plt.title('クラスター別意見数')
plt.tight_layout()
plt.savefig('cluster_chart.png', dpi=150)
plt.show()
```

### クラスター付き散布図

```python
import pandas as pd
import matplotlib.pyplot as plt

# クラスターCSV（UMAP 座標 x, y と各階層のクラスタ ID が入っている）を読み込む
clusters_df = pd.read_csv("outputs/my-analysis/hierarchical_clusters.csv")

# 保存済みの UMAP 座標と第1階層クラスタ ID をそのまま使う
# （レポートと同じ平面・同じクラスタになる。埋め込みから UMAP を測り直す必要はない）
coords = clusters_df[["x", "y"]].to_numpy()
# クラスタ ID は "1_..." のような文字列なので、色分け用に数値コードへ変換する
colors = clusters_df["cluster-level-1-id"].astype("category").cat.codes

# 描画
plt.figure(figsize=(12, 10))
scatter = plt.scatter(coords[:, 0], coords[:, 1], c=colors, cmap='tab10', alpha=0.7, s=40)
plt.colorbar(scatter, label='クラスターID')
plt.title('意見のクラスタリング結果')
plt.xlabel('UMAP 1')
plt.ylabel('UMAP 2')
plt.tight_layout()
plt.savefig('clustered_scatter.png', dpi=150)
plt.show()
```

## 7. カスタムプロンプトの使用

デフォルトプロンプトを上書きできます。

```python
from analysis_core.prompts import get_default_prompt

# デフォルトプロンプトを確認
default_extraction = get_default_prompt("extraction")
print(default_extraction[:200])

# カスタムプロンプトを設定
config = {
    # ...
    "extraction": {
        "workers": 3,
        "limit": 100,
        "prompt": """あなたは政策分析の専門家です。
与えられたコメントから、具体的な政策提案を抽出してください。

# 出力形式
{
  "extractedOpinionList": ["提案1", "提案2"]
}
""",
    },
}
```

## 8. エラーハンドリング

```python
from analysis_core import PipelineOrchestrator

try:
    orchestrator = PipelineOrchestrator.from_dict(config)
    result = orchestrator.run_default()

    if result.success:
        print("分析が完了しました")
    else:
        print(f"エラー: {result.error}")

except FileNotFoundError as e:
    print(f"ファイルが見つかりません: {e}")
except ValueError as e:
    print(f"設定エラー: {e}")
except Exception as e:
    print(f"予期しないエラー: {e}")
```

## 9. 非同期実行

長時間の処理をバックグラウンドで実行する場合：

```python
import concurrent.futures
from analysis_core import PipelineOrchestrator

def run_analysis(config, name):
    orchestrator = PipelineOrchestrator.from_dict(
        config=config,
        output_dir=name
    )
    return orchestrator.run_default()

# 複数の分析を並列実行
configs = [config1, config2, config3]
names = ["analysis1", "analysis2", "analysis3"]

with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
    futures = [
        executor.submit(run_analysis, cfg, name)
        for cfg, name in zip(configs, names)
    ]

    for future in concurrent.futures.as_completed(futures):
        result = future.result()
        print(f"完了: {result.output_dir}")
```

## 10. Jupyter Notebook での利用

```python
# セル1: インストール確認
import analysis_core
print(f"Version: {analysis_core.__version__}")

# セル2: 設定と実行
from analysis_core import PipelineOrchestrator
import os

os.environ["OPENAI_API_KEY"] = "sk-..."

config = {
    "name": "Notebook分析",
    "question": "どのような意見がありますか？",
    "input": "comments",
    "model": "gpt-4o-mini",
    "provider": "openai",
    "is_embedded_at_local": False,
    "extraction": {"workers": 2, "limit": 50},
}

orchestrator = PipelineOrchestrator.from_dict(config)
result = orchestrator.run_default()

# セル3: 結果表示
import json
with open(f"outputs/{config['name']}/hierarchical_result.json") as f:
    data = json.load(f)

from IPython.display import Markdown
Markdown(f"## 分析結果\n\n{data['overview']}")
```

---

CLIでの利用方法は [CLIクイックスタート](cli-quickstart.md) を参照してください。
