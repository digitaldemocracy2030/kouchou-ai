# Python スクリプトからの利用ガイド

このガイドでは、`kouchou-ai-analysis-core` パッケージを Python スクリプトから import して利用する方法を説明します。

## 前提条件

- Python 3.12 以上
- OpenAI API キー

## 1. インストール

```bash
pip install kouchou-ai-analysis-core
```

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
    "hierarchical_clustering": {
        "cluster_nums": [3, 6],
    },
}

# パイプラインを実行
orchestrator = PipelineOrchestrator.from_config(
    config=config,
    output_dir="my-analysis",
    input_base_dir=Path("./inputs"),
    output_base_dir=Path("./outputs"),
)

result = orchestrator.run()

print(f"ステータス: {result['status']}")
print(f"出力ディレクトリ: {result['output_dir']}")
```

### PipelineConfig クラスを使用する

設定の検証やJSONファイルからの読み込みには `PipelineConfig` を使用します。

```python
from analysis_core import PipelineConfig, PipelineOrchestrator

# JSONファイルから読み込み
config = PipelineConfig.from_json("config.json")

# 辞書に変換してオーケストレータに渡す
orchestrator = PipelineOrchestrator.from_config(config.to_dict())
result = orchestrator.run()
```

## 3. 個別ステップの実行

特定のステップだけを実行することもできます。

```python
from analysis_core.steps import (
    extraction,
    embedding,
    hierarchical_clustering,
    hierarchical_initial_labelling,
    hierarchical_merge_labelling,
    hierarchical_overview,
    hierarchical_aggregation,
)

# 各ステップは config 辞書と output_base_dir を受け取る
# extraction(config, output_base_dir)
```

### 抽出のみを実行

```python
from pathlib import Path
from analysis_core.steps import extraction

config = {
    "input": "my-comments",
    "provider": "openai",
    "extraction": {
        "workers": 1,
        "limit": 10,
        "prompt": "あなたは専門的なリサーチアシスタントです...",
        "model": "gpt-4o-mini",
        "properties": [],
    },
}

extraction(config, Path("./outputs/my-analysis"))
```

## 4. 結果の読み込みと利用

### 結果JSONの読み込み

```python
import json
from pathlib import Path

result_path = Path("outputs/my-analysis/hierarchical_result.json")
with open(result_path) as f:
    data = json.load(f)

# 基本情報
print(f"コメント数: {data['comment_num']}")
print(f"要約: {data['overview']}")

# クラスター情報
for cluster in data['clusters']:
    level = cluster.get('level', 0)
    label = cluster.get('label', 'N/A')
    args = cluster.get('arguments', [])
    print(f"{'  ' * level}[{label}] ({len(args)}件)")
```

### 意見データの取得

```python
# 抽出された意見
arguments = data['arguments']
for arg_id, arg in list(arguments.items())[:5]:
    print(f"{arg_id}: {arg['argument']}")

# 元のコメント
comments = data['comments']
for comment_id, comment in list(comments.items())[:5]:
    print(f"{comment_id}: {comment['comment-body'][:50]}...")
```

## 5. Pandas での分析

```python
import pandas as pd
import json

with open("outputs/my-analysis/hierarchical_result.json") as f:
    data = json.load(f)

# 意見をDataFrameに変換
args_list = [
    {"id": k, **v}
    for k, v in data['arguments'].items()
]
df_args = pd.DataFrame(args_list)

print(df_args.head())
print(f"\n意見数: {len(df_args)}")

# クラスター別の集計
if 'cluster-id' in df_args.columns:
    print(df_args.groupby('cluster-id').size())
```

## 6. Matplotlib での可視化

### クラスター別意見数の棒グラフ

```python
import json
import matplotlib.pyplot as plt

# 日本語フォントの設定（環境に応じて変更）
plt.rcParams['font.family'] = 'Hiragino Sans'

with open("outputs/my-analysis/hierarchical_result.json") as f:
    data = json.load(f)

# レベル1のクラスターを取得
clusters = [c for c in data['clusters'] if c.get('level') == 1]
labels = [c['label'][:15] + '...' if len(c['label']) > 15 else c['label']
          for c in clusters]
counts = [len(c.get('arguments', [])) for c in clusters]

plt.figure(figsize=(10, 6))
plt.barh(labels, counts, color='steelblue')
plt.xlabel('意見数')
plt.title('クラスター別意見数')
plt.tight_layout()
plt.savefig('cluster_chart.png', dpi=150)
plt.show()
```

### UMAP埋め込みの散布図

```python
import pickle
import numpy as np
import matplotlib.pyplot as plt
from umap import UMAP

# 埋め込みベクトルの読み込み
with open("outputs/my-analysis/embeddings.pkl", "rb") as f:
    embeddings = pickle.load(f)

# numpy配列に変換
vectors = np.array(list(embeddings.values()))

# UMAPで2次元に削減
reducer = UMAP(n_components=2, random_state=42)
coords = reducer.fit_transform(vectors)

# 散布図の描画
plt.figure(figsize=(10, 8))
plt.scatter(coords[:, 0], coords[:, 1], alpha=0.6, s=30)
plt.title('意見の分布（UMAP）')
plt.xlabel('UMAP 1')
plt.ylabel('UMAP 2')
plt.tight_layout()
plt.savefig('umap_scatter.png', dpi=150)
plt.show()
```

### クラスター付き散布図

```python
import pickle
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from umap import UMAP

# データ読み込み
with open("outputs/my-analysis/hierarchical_result.json") as f:
    data = json.load(f)

with open("outputs/my-analysis/embeddings.pkl", "rb") as f:
    embeddings = pickle.load(f)

# クラスターCSVを読み込み
clusters_df = pd.read_csv("outputs/my-analysis/hierarchical_clusters.csv")

# 埋め込みとクラスターを結合
arg_ids = list(embeddings.keys())
vectors = np.array([embeddings[aid] for aid in arg_ids])

# UMAP変換
reducer = UMAP(n_components=2, random_state=42)
coords = reducer.fit_transform(vectors)

# クラスターラベルを取得
cluster_map = dict(zip(clusters_df['arg-id'], clusters_df['cluster-id-lv1']))
colors = [cluster_map.get(aid, -1) for aid in arg_ids]

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
    orchestrator = PipelineOrchestrator.from_config(config)
    result = orchestrator.run()

    if result['status'] == 'completed':
        print("分析が完了しました")
    else:
        print(f"エラー: {result.get('error')}")

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
    orchestrator = PipelineOrchestrator.from_config(
        config,
        output_dir=name
    )
    return orchestrator.run()

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
        print(f"完了: {result['output_dir']}")
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
    "hierarchical_clustering": {"cluster_nums": [3, 6]},
}

orchestrator = PipelineOrchestrator.from_config(config)
result = orchestrator.run()

# セル3: 結果表示
import json
with open(f"outputs/{config['name']}/hierarchical_result.json") as f:
    data = json.load(f)

from IPython.display import Markdown
Markdown(f"## 分析結果\n\n{data['overview']}")
```

---

CLIでの利用方法は [CLI_QUICKSTART.md](CLI_QUICKSTART.md) を参照してください。
