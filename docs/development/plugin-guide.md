# プラグイン開発ガイド

kouchou-ai には3種類のプラグインシステムがあります：

1. **入力プラグイン** - 外部サービス（YouTube、Twitter等）からデータを取得
2. **分析プラグイン** - 分析パイプラインの処理ステップをカスタマイズ
3. **可視化プラグイン** - 分析結果の表示・可視化をカスタマイズ

自作プラグインの私的利用・配布・サービス提供の違いは、[ライセンスと結果の公開](../user-guide/license.md)を参照してください。

サンプルとして YouTube 入力プラグインと階層リスト可視化プラグインを同梱しています。
入力は環境変数、可視化は `visualization_config` で有効化する運用です。

---

# Part 1: 入力プラグイン（Input Plugins）

Admin UIから外部サービスのデータを取り込むためのプラグインシステムです。

## 概要

入力プラグインにより：

- YouTube、Twitter等の外部サービスからコメント/投稿を取得
- プラグインごとに必要な設定（APIキー等）を宣言的に管理
- 設定不備の早期検出（サーバー起動時にエラー）
- Admin UIでのプラグイン表示を自動化

## クイックスタート：新しい入力プラグインの作成

### Step 1: プラグインファイルを作成

`apps/api/src/plugins/` に新しいPythonファイルを作成します。

```python
# apps/api/src/plugins/twitter.py
"""
Twitter input plugin for fetching tweets.
"""

from typing import Any

import polars as pl

from src.plugins.base import InputPlugin, PluginManifest, PluginSetting, SettingType
from src.plugins.registry import PluginRegistry


@PluginRegistry.register
class TwitterPlugin(InputPlugin):
    """Twitter投稿を取得するプラグイン"""

    manifest = PluginManifest(
        id="twitter",                          # 一意のID
        name="Twitter",                        # 表示名
        description="Twitterの投稿を取得します。",  # 説明
        version="1.0.0",                       # バージョン
        icon="twitter",                        # アイコン識別子
        placeholder="https://twitter.com/...", # URL入力欄のプレースホルダー
        enabled_by_default=False,              # デフォルトで無効
        settings=[                             # 必要な設定
            PluginSetting(
                key="TWITTER_API_KEY",
                label="Twitter API Key",
                description="Twitter API v2のAPIキー",
                setting_type=SettingType.SECRET,
                required=True,
            ),
            PluginSetting(
                key="TWITTER_API_SECRET",
                label="Twitter API Secret",
                description="Twitter API v2のAPIシークレット",
                setting_type=SettingType.SECRET,
                required=True,
            ),
        ],
    )

    def validate_source(self, source: str) -> tuple[bool, str | None]:
        """ソースURL/IDの検証"""
        if "twitter.com" not in source and "x.com" not in source:
            return False, "無効なTwitter URLです"
        return True, None

    def fetch_data(self, source: str, **options: Any) -> pl.DataFrame:
        """データを取得して polars の DataFrame で返す"""
        # 設定が完了しているか確認（必須）
        self.ensure_configured()

        # URL検証
        is_valid, error = self.validate_source(source)
        if not is_valid:
            raise ValueError(error)

        # APIキーを取得
        api_key = self.manifest.settings[0].get_value()
        api_secret = self.manifest.settings[1].get_value()

        # データ取得処理...
        # (Twitter API呼び出しを実装)

        # 必須カラム: comment-id, comment-body, source, url
        # オプション: attribute_* で追加属性
        return pl.DataFrame([
            {
                "comment-id": "tweet_123",
                "comment-body": "投稿内容",
                "source": "Twitter",
                "url": "https://twitter.com/...",
                "attribute_author": "@username",
                "attribute_likes": 100,
            }
        ])
```

### Step 2: 環境変数を設定

`.env` ファイルにプラグインの有効化と設定を追加：

```bash
# プラグインを有効化（必須）
ENABLE_TWITTER_INPUT_PLUGIN=true

# プラグイン固有の設定
TWITTER_API_KEY=your-api-key
TWITTER_API_SECRET=your-api-secret
```

**以上で完了です！** `registry.py` や Admin UI の修正は不要です。

## プラグインの動作

### 有効化の仕組み

| 環境変数 | APIキー | 動作 |
|---------|---------|------|
| 未設定 | - | プラグイン無効（Admin UIに「設定が必要です」と表示）|
| `=true` | 未設定 | **サーバー起動エラー**（設定漏れを早期検出）|
| `=true` | 設定済み | プラグイン有効（Admin UIで使用可能）|

### 自動検出の仕組み

`src/plugins/` 配下のPythonファイルは自動的に検出・登録されます：

```
apps/api/src/plugins/
├── __init__.py      # エクスポート（変更不要）
├── base.py          # 基底クラス（変更不要）
├── registry.py      # レジストリ（変更不要）
├── youtube.py       # YouTubeプラグイン
└── twitter.py       # 新規追加 → 自動で登録される
```

## PluginManifest フィールド

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `id` | `str` | 一意のプラグインID（例: `"youtube"`, `"twitter"`）|
| `name` | `str` | Admin UIに表示される名前 |
| `description` | `str` | プラグインの説明 |
| `version` | `str` | セマンティックバージョン（例: `"1.0.0"`）|
| `icon` | `str \| None` | アイコン識別子（将来のUI用）|
| `placeholder` | `str` | URL入力フィールドのプレースホルダー |
| `enabled_by_default` | `bool` | `False` を推奨（明示的有効化が必要）|
| `settings` | `list[PluginSetting]` | 必要な設定のリスト |

## PluginSetting フィールド

| フィールド | 型 | 説明 |
|-----------|-----|------|
| `key` | `str` | 環境変数名（例: `"YOUTUBE_API_KEY"`）|
| `label` | `str` | Admin UIに表示されるラベル |
| `description` | `str` | 設定の説明 |
| `setting_type` | `SettingType` | `STRING`, `SECRET`, `INTEGER`, `BOOLEAN`, `URL` |
| `required` | `bool` | 必須かどうか |
| `default` | `Any` | デフォルト値（`required=False` の場合）|

## fetch_data の戻り値

`fetch_data()` は以下のカラムを持つ `polars.DataFrame` を返す必要があります（pandas の DataFrame ではありません。API の依存には pandas が含まれていないため、`import pandas` するとプラグインが読み込まれません）：

### 必須カラム

| カラム名 | 説明 |
|---------|------|
| `comment-id` | コメントの一意ID |
| `comment-body` | コメント本文 |
| `source` | ソース名（例: `"YouTube"`, `"Twitter"`）|
| `url` | 元のコメントへのURL |

### オプションカラム（属性）

`attribute_` プレフィックスで追加属性を含められます：

```python
{
    "attribute_author": "投稿者名",
    "attribute_published_at": "2024-01-01T00:00:00Z",
    "attribute_like_count": 100,
    "attribute_video_title": "動画タイトル",
}
```

## 依存関係の追加

外部ライブラリが必要な場合、`apps/api/pyproject.toml` にオプション依存として追加：

```toml
[project.optional-dependencies]
youtube = ["google-api-python-client>=2.150.0"]
twitter = ["tweepy>=4.14.0"]
all-plugins = [
    "google-api-python-client>=2.150.0",
    "tweepy>=4.14.0",
]
```

インストール：

```bash
pip install -e ".[twitter]"
# または全プラグイン
pip install -e ".[all-plugins]"
```

## 既存プラグイン: YouTube

参考実装として `apps/api/src/plugins/youtube.py` を参照してください。

**機能:**
- YouTube動画URLからコメントを取得
- プレイリストURLから複数動画のコメントを一括取得
- 返信コメントの取得（オプション）

**環境変数:**
```bash
ENABLE_YOUTUBE_INPUT_PLUGIN=true
YOUTUBE_API_KEY=your-youtube-data-api-v3-key
```

---

# Part 2: 分析プラグイン（Analysis Plugins）

analysis-core のプラグインシステムを使用して、カスタム分析ステップを追加する方法を説明します。

## 概要

analysis-core は、分析パイプラインの各ステップをプラグインとして実装するアーキテクチャを採用しています。これにより：

- コアコードを変更せずに新しい分析ステップを追加できる
- 既存のステップを置き換えたり拡張したりできる
- ワークフロー定義で柔軟にステップを組み合わせられる

## プラグインの種類

### 1. 組み込みプラグイン

`analysis_core.plugins.builtin` に含まれる標準プラグイン：

| プラグインID | 説明 |
|-------------|------|
| `analysis.extraction` | コメントから意見を抽出 |
| `analysis.opinion_classification` | 意見ごとに yes/no ラベル（侮辱・ヘイト表現、政策提案）を付与（任意、既定は無効） |
| `analysis.opinion_stance` | 意見ごとに対象への賛否スコア（-1.0〜+1.0）を付与（任意、既定は無効） |
| `analysis.embedding` | 埋め込みベクトル生成 |
| `analysis.opinion_novelty` | 意見ごとに他の意見からの遠さ（新規性 0.0〜1.0）を埋め込みから付与（任意、既定は無効、LLM 不使用） |
| `analysis.hierarchical_clustering` | 階層クラスタリング |
| `analysis.hierarchical_initial_labelling` | 初期ラベリング |
| `analysis.hierarchical_merge_labelling` | 統合ラベリング |
| `analysis.hierarchical_overview` | 概要生成 |
| `analysis.hierarchical_aggregation` | 結果集約 |
| `analysis.hierarchical_visualization` | 可視化HTML生成 |

### 2. 外部プラグイン

`plugins/analysis/` ディレクトリに配置するカスタムプラグイン。

## クイックスタート：関数ベースプラグイン

最も簡単なプラグイン作成方法は `@step_plugin` デコレータを使用することです。

```python
# my_plugin.py
import polars as pl

from analysis_core.plugin import (
    step_plugin,
    StepContext,
    StepInputs,
    StepOutputs,
)

@step_plugin(
    id="mycompany.custom_analysis",
    version="1.0.0",
    name="Custom Analysis",
    description="カスタム分析ステップ",
    inputs=["arguments"],  # 依存するアーティファクト
    outputs=["custom_result"],  # 生成するアーティファクト
    use_llm=False,  # LLMを使用するかどうか
)
def custom_analysis_plugin(
    ctx: StepContext,
    inputs: StepInputs,
    config: dict,
) -> StepOutputs:
    """カスタム分析を実行"""

    # 入力ファイル（抽出された意見の args.csv）を読み込み
    args_path = inputs.artifacts["arguments"]
    args_df = pl.read_csv(args_path)

    # 処理を実行（例: 意見ごとの文字数を数える）
    result_df = args_df.with_columns(pl.col("argument").str.len_chars().alias("length"))

    # 結果を保存
    output_path = ctx.output_dir / "custom_result.csv"
    result_df.write_csv(output_path)

    return StepOutputs(
        artifacts={"custom_result": output_path},
        token_usage=0,
    )
```

## プラグインインターフェース

### StepContext

ステップ実行時のコンテキスト情報：

```python
@dataclass
class StepContext:
    output_dir: Path      # 出力ディレクトリ
    input_dir: Path       # 入力ディレクトリ
    dataset: str          # データセット名
    provider: str         # LLMプロバイダー (openai, azure, etc.)
    model: str            # LLMモデル名
    local_llm_address: str | None  # ローカルLLMアドレス
    user_api_key: str | None       # ユーザーAPIキー
```

### StepInputs

ステップへの入力：

```python
@dataclass
class StepInputs:
    artifacts: dict[str, Path]  # アーティファクトID → ファイルパス
    config: dict[str, Any]      # 追加の設定
```

### StepOutputs

ステップからの出力：

```python
@dataclass
class StepOutputs:
    artifacts: dict[str, Path]  # 生成したアーティファクト
    token_usage: int = 0        # 使用したトークン数
    token_input: int = 0        # 入力トークン数
    token_output: int = 0       # 出力トークン数
    metadata: dict[str, Any]    # 追加のメタデータ
```

## 外部プラグインの作成

### ディレクトリ構造

```
plugins/analysis/
└── my-custom-step/
    ├── manifest.yaml    # プラグインメタデータ
    └── plugin.py        # プラグイン実装
```

### manifest.yaml

```yaml
id: mycompany.custom_step
version: "1.0.0"
name: "My Custom Step"
description: "カスタム分析ステップの説明"
entry: plugin:custom_step_plugin  # モジュール:属性名

inputs:
  - arguments
  - clusters

outputs:
  - custom_result

use_llm: false

# オプション: 設定スキーマ
config_schema:
  type: object
  properties:
    threshold:
      type: number
      default: 0.5
```

### plugin.py

```python
from analysis_core.plugin import (
    step_plugin,
    StepContext,
    StepInputs,
    StepOutputs,
)

@step_plugin(
    id="mycompany.custom_step",
    version="1.0.0",
    name="My Custom Step",
    description="カスタム分析ステップ",
    inputs=["arguments", "clusters"],
    outputs=["custom_result"],
)
def custom_step_plugin(
    ctx: StepContext,
    inputs: StepInputs,
    config: dict,
) -> StepOutputs:
    # 設定を取得
    threshold = config.get("threshold", 0.5)

    # 入力を読み込み
    args_path = inputs.artifacts.get("arguments")
    clusters_path = inputs.artifacts.get("clusters")

    # 処理...

    # 出力
    output_path = ctx.output_dir / "custom_result.json"
    return StepOutputs(artifacts={"custom_result": output_path})
```

## プラグインの登録と使用

### 手動登録

```python
from analysis_core.plugin import get_registry

# グローバルレジストリを取得
registry = get_registry()

# 組み込みプラグインを登録
registry.register_builtin_plugins()

# カスタムプラグインを登録
registry.register(custom_step_plugin)

# プラグインを取得
plugin = registry.get("mycompany.custom_step")
```

### ディレクトリから読み込み

```python
from pathlib import Path
from analysis_core.plugin import (
    load_plugins_from_directory,
    get_registry,
)

# プラグインディレクトリから読み込み
plugins_dir = Path("plugins/analysis")
loaded = load_plugins_from_directory(plugins_dir, get_registry())

print(f"Loaded {len(loaded)} plugins")
for p in loaded:
    print(f"  - {p.manifest.id} v{p.manifest.version}")
```

### 環境変数で指定

`ANALYSIS_PLUGINS_PATH` は、Python API の `load_all_plugins()`（内部で `discover_plugin_directories()`）が読むプラグインディレクトリの一覧です。区切りは OS のパス区切り（Linux / macOS は `:`）です。

```python
from analysis_core.plugin import get_registry, load_all_plugins
from analysis_core.workflow import WorkflowEngine

# ANALYSIS_PLUGINS_PATH=/path/to/plugins:/another/path を設定して実行する。
# 組み込みプラグインを先に登録し、そのあと外部プラグインを登録する（同じ ID は外部側で置き換える）
loaded = load_all_plugins(get_registry())

engine = WorkflowEngine()  # 読み込んだ外部プラグインを含むグローバルレジストリを使う
```

`load_all_plugins()` は `ANALYSIS_PLUGINS_PATH` のほかに、カレントディレクトリの `plugins/analysis/` も探します。信頼できないディレクトリで実行しないでください。

**注意**: CLI（`kouchou-analyze` / `python -m analysis_core`）と、管理画面からのレポート作成（API が CLI を起動する経路）は、外部プラグインを読み込みません。`ANALYSIS_PLUGINS_PATH` を設定しても無視され、組み込みのステップで実行されます。外部プラグインで組み込みのステップを置き換えたり新しいステップを使ったりするには、上のように Python API で読み込み、`WorkflowEngine` でワークフローを実行してください。

## ワークフローでの使用

カスタムプラグインをワークフローで使用するには：

```python
from analysis_core.workflow import WorkflowDefinition, WorkflowStep

workflow = WorkflowDefinition(
    id="custom-workflow",
    version="1.0.0",
    name="Custom Analysis Workflow",
    steps=[
        WorkflowStep(
            id="extract",
            plugin="analysis.extraction",
        ),
        WorkflowStep(
            id="embed",
            plugin="analysis.embedding",
            depends_on=["extract"],
        ),
        WorkflowStep(
            id="custom",
            plugin="mycompany.custom_step",  # カスタムプラグイン
            depends_on=["extract"],
            config={"threshold": 0.7},
        ),
    ],
)
```

## LLMを使用するプラグイン

LLMを使用するプラグインの例：

```python
# my_llm_plugin.py
import json

import polars as pl

from analysis_core.plugin import StepContext, StepInputs, StepOutputs, step_plugin
from analysis_core.services.llm import request_to_chat_ai


@step_plugin(
    id="mycompany.llm_analysis",
    version="1.0.0",
    inputs=["arguments"],
    outputs=["analysis_result"],
    use_llm=True,  # LLM使用フラグ
)
def llm_analysis_plugin(
    ctx: StepContext,
    inputs: StepInputs,
    config: dict,
) -> StepOutputs:
    # プロンプトを取得（configから、またはデフォルト）
    prompt = config.get("prompt", "Analyze the following...")
    model = config.get("model", ctx.model)

    # 分析対象の意見を読み込み
    arguments = pl.read_csv(inputs.artifacts["arguments"])["argument"].to_list()

    # LLMリクエスト
    # 戻り値は (応答テキスト, 入力トークン数, 出力トークン数, 合計トークン数) のタプル
    response_text, token_input, token_output, token_total = request_to_chat_ai(
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": "\n".join(arguments)},
        ],
        model=model,
        provider=ctx.provider,
        local_llm_address=ctx.local_llm_address,
        user_api_key=ctx.user_api_key,
    )

    # 結果を保存
    output_path = ctx.output_dir / "analysis_result.json"
    output_path.write_text(json.dumps({"result": response_text}, ensure_ascii=False), encoding="utf-8")

    # トークン使用量を記録
    return StepOutputs(
        artifacts={"analysis_result": output_path},
        token_usage=token_total,
        token_input=token_input,
        token_output=token_output,
    )
```

## テスト

クイックスタートの `custom_analysis_plugin`（`my_plugin.py`）のテスト例です。pytest の `tmp_path` に入力ファイルを用意して実行します。

`@step_plugin` を付けた関数は `FunctionPlugin` オブジェクトに置き換わるため、関数のように直接呼び出すことはできません。`.run(ctx, inputs, config)` で実行してください。

```python
from pathlib import Path

from analysis_core.plugin import StepContext, StepInputs

from my_plugin import custom_analysis_plugin


def test_custom_analysis_plugin(tmp_path: Path):
    # テスト用の入力ファイル
    args_path = tmp_path / "args.csv"
    args_path.write_text("arg-id,argument\nA1_0,公園を増やしてほしい\n", encoding="utf-8")

    # テスト用コンテキスト
    ctx = StepContext(
        output_dir=tmp_path,
        input_dir=tmp_path,
        dataset="test",
        provider="openai",
        model="gpt-4o-mini",
    )

    # テスト用入力
    inputs = StepInputs(artifacts={"arguments": args_path})

    # プラグイン実行（直接呼び出しではなく run() を使う）
    result = custom_analysis_plugin.run(ctx, inputs, {})

    # 検証
    assert result.artifacts["custom_result"].exists()
```

LLM を使うプラグインをテストするときは、`unittest.mock.patch("my_llm_plugin.request_to_chat_ai", return_value=("応答", 10, 5, 15))` のように LLM の呼び出しを差し替えると、API を呼ばずに確かめられます。

## ベストプラクティス

1. **ID命名規則**: `organization.step_name` 形式を使用（例: `mycompany.sentiment_analysis`）

2. **バージョニング**: セマンティックバージョニングを使用（例: `1.0.0`）

3. **入出力の明示**: `inputs` と `outputs` を明確に定義して依存関係を明示

4. **エラーハンドリング**: 適切な例外処理を実装

5. **トークン追跡**: LLM使用時は `token_usage` を正確に報告

6. **設定スキーマ**: `config_schema` でバリデーション可能な設定を定義

## トラブルシューティング

### プラグインが見つからない

```
PluginNotFoundError: Plugin 'mycompany.custom_step' not found
```

解決策：
- manifest.yaml の `id` とコードの `id` が一致しているか確認
- `entry` フィールドのモジュール名と属性名が正しいか確認
- プラグインディレクトリが正しく設定されているか確認

### インポートエラー

```
PluginLoadError: Import error: No module named 'some_dependency'
```

解決策：
- プラグインが必要とする依存関係がインストールされているか確認
- 依存関係を `pyproject.toml` または `requirements.txt` に追加

### 型エラー

```
PluginLoadError: Attribute 'plugin' is not an AnalysisStepPlugin
```

解決策：
- `@step_plugin` デコレータが正しく適用されているか確認
- 関数シグネチャが正しいか確認（`ctx`, `inputs`, `config` の3引数）

---

# Part 3: 可視化プラグイン（Visualization Plugins）

分析結果の表示・可視化をカスタマイズするためのプラグインシステムです。

## 概要

可視化プラグインにより：

- 分析結果のグラフ・チャートのカスタマイズ
- 新しい可視化コンポーネントの追加
- チャートモードの追加・削除
- レポートごとに表示するチャートの設定

## アーキテクチャ

```
apps/public-viewer/components/charts/
├── plugins/
│   ├── types.ts          # プラグインの型定義
│   ├── registry.ts       # プラグインレジストリ
│   ├── scatter.tsx       # 散布図プラグイン (scatterAll, scatterDetail, scatterDensity)
│   ├── treemap.tsx       # ツリーマップ プラグイン
│   └── hierarchy-list.tsx # 階層リストプラグイン
├── ScatterChart.tsx       # 散布図コンポーネント
├── TreemapChart.tsx       # ツリーマップコンポーネント
├── HierarchyListChart.tsx # 階層リストコンポーネント
└── SelectChartButton.tsx  # チャート選択UI
```

## クイックスタート：新しいチャートプラグインの作成

### Step 1: チャートコンポーネントを作成

```tsx
// apps/public-viewer/components/charts/MyCustomChart.tsx
import type { Argument, Cluster } from "@/type";

type Props = {
  clusterList: Cluster[];
  argumentList: Argument[];
  onHover?: () => void;
  filteredArgumentIds?: string[];
};

export function MyCustomChart({ clusterList, argumentList, filteredArgumentIds }: Props) {
  return (
    <div>
      {/* チャートの実装 */}
    </div>
  );
}
```

### Step 2: プラグインファイルを作成

```tsx
// apps/public-viewer/components/charts/plugins/my-custom.tsx
// アイコンは既存のものを使う例。独自のアイコンを使う場合は components/icons/ViewIcons.tsx に追加する
import { ListViewIcon as MyCustomIcon } from "@/components/icons/ViewIcons";
import { MyCustomChart } from "../MyCustomChart";
import type { ChartPlugin, ChartRenderContext } from "./types";

export const myCustomPlugin: ChartPlugin = {
  manifest: {
    id: "my-custom",                    // 一意のプラグインID
    name: "カスタムチャート",           // 表示名
    description: "カスタム可視化を表示", // 説明
    version: "1.0.0",                   // バージョン
    icon: MyCustomIcon,                 // アイコンコンポーネント
    modes: [                            // このプラグインが提供するモード
      {
        id: "customView",               // モードID（レポートの enabledCharts に加えるID。Step 5 参照）
        label: "カスタム",              // 表示ラベル
        icon: MyCustomIcon,
      },
    ],
  },

  canHandle: (mode: string) => {
    return mode === "customView";
  },

  render: (context: ChartRenderContext) => {
    const { result, filteredArgumentIds, onHover } = context;

    return (
      <MyCustomChart
        clusterList={result.clusters}
        argumentList={result.arguments}
        onHover={onHover}
        filteredArgumentIds={filteredArgumentIds}
      />
    );
  },
};
```

### Step 3: ChartTypeは更新不要（任意）

ChartType は既知のID + 任意文字列を許容するため、サーバや共有スキーマの更新は不要です。
補完を強くしたい場合のみ、型定義の例を参考にしてください。

```typescript
// apps/public-viewer/type.ts
export type ChartType =
  | "scatterAll"
  | "scatterDetail"
  | "scatterDensity"
  | "treemap"
  | "hierarchyList"
  | (string & {});
```

### Step 4: レジストリにプラグインを登録

```typescript
// apps/public-viewer/components/charts/plugins/registry.ts
import { myCustomPlugin } from "./my-custom";

export function loadBuiltinChartPlugins(): void {
  // ... 既存のプラグイン登録
  chartRegistry.register(myCustomPlugin);
}
```

### Step 5: レポートで表示を有効にする

レジストリに登録しただけでは、新しいモードはどのレポートのタブにも表示されません。公開ビューアは、レポートの可視化設定 `enabledCharts` に含まれるモードだけを表示するためです（[レポートごとのチャート設定](#レポートごとのチャート設定)）。

- 可視化設定を保存していないレポートでは、ビューアの既定値（`DEFAULT_ENABLED_CHARTS` の `scatterAll` / `scatterDetail` / `scatterDensity` / `treemap` に `hierarchyList` を加えたもの）が使われます
- 管理画面の可視化設定ダイアログは、選べるチャートが固定の一覧（`AVAILABLE_CHARTS`）なので、新しいモードを選べません

表示するレポートごとに、管理用 API（`PATCH /admin/reports/{slug}/visualization-config`）で `enabledCharts`（必要なら `chartOrder`・`defaultChart`）にモード ID を加えます。この API は設定全体を置き換えます（送らなかった項目は既定値に戻ります）。先に `GET /admin/reports/{slug}/visualization-config` で今の設定を取得し、それにモード ID を加えて送ってください。

```bash
# 今の設定を取得し、enabledCharts に customView を加えて送り直す
# （設定が未保存なら、ビューアの既定の 5 種に customView を加えたものを保存する）
curl -s "http://localhost:8000/admin/reports/<slug>/visualization-config" \
  -H "x-api-key: <ADMIN_API_KEY>" \
  | jq '(.visualizationConfig // {"version": "1", "enabledCharts": ["scatterAll", "scatterDetail", "scatterDensity", "treemap", "hierarchyList"]})
        | .enabledCharts += ["customView"]' \
  | curl -s -X PATCH "http://localhost:8000/admin/reports/<slug>/visualization-config" \
      -H "x-api-key: <ADMIN_API_KEY>" \
      -H "Content-Type: application/json" \
      -d @-
```

API で加えたモード ID は、その後に管理画面のダイアログで設定を保存しても残ります。

すべてのレポートで既定で表示したい場合は、ビューアの既定値を変更します。既定値は次のように複数の場所にあり、それぞれ値が違うので注意してください。

| 場所 | 使われる場面 |
|------|------------|
| `apps/public-viewer/components/charts/SelectChartButton.tsx` の `DEFAULT_ENABLED_CHARTS` | 可視化設定が無いときの既定（下の `DEFAULT_READING_CHARTS` の元） |
| `apps/public-viewer/components/report/ClientContainer.tsx` の `DEFAULT_READING_CHARTS` | 可視化設定を保存していないレポートを表示するとき |
| `apps/api/src/schemas/visualization_config.py` の `DEFAULT_REPORT_DISPLAY_CONFIG` | 保存された可視化設定を読めなかったとき |
| `apps/admin/app/_components/ReportCard/VisualizationConfigDialog/VisualizationConfigDialog.tsx` の `DEFAULT_CONFIG` と `AVAILABLE_CHARTS` | 管理画面のダイアログの初期値と選択肢 |

## プラグインインターフェース

### ChartPlugin

```typescript
interface ChartPlugin {
  /** プラグインのメタデータ */
  manifest: ChartPluginManifest;

  /** 指定されたモードを処理できるか判定 */
  canHandle: (mode: string) => boolean;

  /** チャートをレンダリング */
  render: (context: ChartRenderContext) => React.ReactNode;
}
```

### ChartPluginManifest

```typescript
interface ChartPluginManifest {
  /** 一意のプラグインID */
  id: string;
  /** 表示名 */
  name: string;
  /** 説明 */
  description: string;
  /** バージョン（semver） */
  version: string;
  /** アイコンコンポーネント */
  icon: ComponentType;
  /** このプラグインが提供するモード */
  modes: ChartMode[];
}
```

### ChartMode

```typescript
interface ChartMode {
  /** モードID（selectedChartの値） */
  id: string;
  /** 表示ラベル */
  label: string;
  /** アイコンコンポーネント */
  icon: ComponentType;
  /** データに基づいて無効化できるか */
  canBeDisabled?: boolean;
  /** 無効化判定関数 */
  isDisabled?: (result: Result) => boolean;
  /** 無効時のツールチップ */
  disabledTooltip?: string;
}
```

### ChartRenderContext

```typescript
interface ChartRenderContext {
  /** 分析結果データ */
  result: Result;
  /** 選択中のチャートモード */
  selectedChart: string;
  /** フルスクリーンモードか */
  isFullscreen: boolean;
  /** フィルター適用時の引数ID */
  filteredArgumentIds?: string[];
  /** クラスターラベル表示 */
  showClusterLabels?: boolean;
  /** ツリーマップのズームレベル */
  treemapLevel?: string;
  /** ツリーマップナビゲーション */
  onTreeZoom?: (level: string) => void;
  /** ホバーイベント */
  onHover?: () => void;
}
```

## 組み込みプラグイン

### 1. Scatter Plugin (`scatter`)

散布図を表示するプラグイン。3つのモードを提供：

| モード | 説明 |
|--------|------|
| `scatterAll` | 全データの散布図表示 |
| `scatterDetail` | 詳細クラスタ（下の階層）で色分けした散布図表示 |
| `scatterDensity` | 密度フィルター適用済み表示（条件付きで無効化） |

### 2. Treemap Plugin (`treemap`)

階層構造をツリーマップで可視化。

| モード | 説明 |
|--------|------|
| `treemap` | 階層ツリーマップ表示 |

### 3. Hierarchy List Plugin (`hierarchy-list`)

クラスタを展開可能なリストで表示。

| モード | 説明 |
|--------|------|
| `hierarchyList` | 階層リスト表示 |

## レポートごとのチャート設定

### visualization_config

レポートごとに表示するチャートを設定できます：

```typescript
// apps/public-viewer/type.ts
interface ReportDisplayConfig {
  version: string;
  /** 有効なチャートタイプ */
  enabledCharts: ChartType[];
  /** デフォルトで表示するチャート */
  defaultChart?: ChartType;
  /** チャートの表示順序 */
  chartOrder?: ChartType[];
  /** チャート固有のパラメータ */
  params?: DisplayParams;
}
```

### 使用例

```json
{
  "visualizationConfig": {
    "version": "1.0",
    "enabledCharts": ["treemap", "hierarchyList"],
    "defaultChart": "hierarchyList",
    "chartOrder": ["hierarchyList", "treemap"]
  }
}
```

これにより、散布図を非表示にしてツリーマップと階層リストのみを表示できます。

## 条件付きモード無効化

特定の条件でモードを無効化できます：

```typescript
modes: [
  {
    id: "scatterDensity",
    label: "濃い意見",
    icon: DenseViewIcon,
    canBeDisabled: true,
    isDisabled: (result) => {
      // 最大レベルが1以下の場合は無効
      const maxLevel = Math.max(...result.clusters.map((c) => c.level));
      return maxLevel <= 1;
    },
    disabledTooltip: "この設定条件では抽出できませんでした",
  },
]
```

## プラグインレジストリ

### 主要メソッド

```typescript
// プラグイン登録
chartRegistry.register(plugin: ChartPlugin): void;

// プラグイン取得
chartRegistry.get(pluginId: string): ChartPlugin | undefined;

// モードからプラグイン取得
chartRegistry.getByMode(modeId: string): ChartPlugin | undefined;

// 全モード取得
chartRegistry.getAllModes(): ChartMode[];

// モード存在チェック
chartRegistry.hasMode(modeId: string): boolean;
```

### 衝突検出

レジストリは重複するプラグインIDやモードIDを検出し、警告を出力します：

```
Chart plugin collision: "scatter" is already registered. Overwriting with new plugin (v2.0.0).
Chart mode collision: "scatterAll" is already registered by plugin "scatter". Overwriting with plugin "scatter-v2".
```

## テスト

プラグインのテスト例：

```typescript
// components/charts/plugins/__tests__/plugins.test.tsx
import { myCustomPlugin } from "../my-custom";

describe("myCustomPlugin", () => {
  it("has correct plugin ID", () => {
    expect(myCustomPlugin.manifest.id).toBe("my-custom");
  });

  it("canHandle returns true for customView", () => {
    expect(myCustomPlugin.canHandle("customView")).toBe(true);
  });

  it("renders without error", () => {
    const result = { clusters: [], arguments: [], config: { title: "Test" } };
    const element = myCustomPlugin.render({
      result,
      selectedChart: "customView",
      isFullscreen: false,
    });
    expect(element).not.toBeNull();
  });
});
```

## バリデーションシステム

プラグインシステムには、コンパイル時チェックに似た事前検証機能があります。これにより、実行時のデバッグ困難なバグを早期に検出できます。

### バリデーション関数

```typescript
import {
  validatePlugin,
  validatePluginManifest,
  validateChartMode,
  validateVisualizationConfig,
  validateResultData,
  formatValidationResult,
  assertValidation,
  logValidationWarnings,
} from "@/components/charts/plugins";
```

| 関数 | 用途 |
|------|------|
| `validatePlugin(plugin)` | プラグイン全体を検証 |
| `validatePluginManifest(manifest)` | マニフェストのみを検証 |
| `validateChartMode(mode, pluginId)` | 個別モードを検証 |
| `validateVisualizationConfig(config, registry)` | visualization_configを検証 |
| `validateResultData(result)` | 結果データ構造を検証 |
| `formatValidationResult(result)` | 検証結果をフォーマット |
| `assertValidation(result, context)` | エラー時に例外をスロー |
| `logValidationWarnings(result, context)` | 警告をコンソールに出力 |

### エラーコード

#### マニフェスト関連 (MANIFEST_*)

| コード | 重要度 | 説明 |
|--------|--------|------|
| `MANIFEST_MISSING_ID` | error | プラグインIDが未定義 |
| `MANIFEST_MISSING_NAME` | error | 表示名が未定義 |
| `MANIFEST_MISSING_VERSION` | error | バージョンが未定義 |
| `MANIFEST_INVALID_VERSION_FORMAT` | warning | semver形式でないバージョン |
| `MANIFEST_MISSING_ICON` | error | アイコンが未定義 |
| `MANIFEST_MODES_NOT_ARRAY` | error | modesが配列でない |
| `MANIFEST_NO_MODES` | warning | モードが定義されていない |
| `MANIFEST_DUPLICATE_MODE_IDS` | error | モードIDが重複 |

#### モード関連 (MODE_*)

| コード | 重要度 | 説明 |
|--------|--------|------|
| `MODE_MISSING_ID` | error | モードIDが未定義 |
| `MODE_MISSING_LABEL` | error | ラベルが未定義 |
| `MODE_MISSING_ICON` | error | アイコンが未定義 |
| `MODE_ISDISABLED_WITHOUT_FLAG` | warning | isDisabledがあるがcanBeDisabledがfalse |
| `MODE_CANBEDISABLED_WITHOUT_ISDISABLED` | warning | canBeDisabledがtrueだがisDisabledがない |

#### プラグイン関連 (PLUGIN_*)

| コード | 重要度 | 説明 |
|--------|--------|------|
| `PLUGIN_CANHANDLE_NOT_FUNCTION` | error | canHandleが関数でない |
| `PLUGIN_CANHANDLE_MISMATCH` | error | canHandleが宣言モードでfalseを返す |
| `PLUGIN_CANHANDLE_THROWS` | error | canHandleが例外をスロー |
| `PLUGIN_RENDER_NOT_FUNCTION` | error | renderが関数でない |

#### 設定関連 (CONFIG_*)

| コード | 重要度 | 説明 |
|--------|--------|------|
| `CONFIG_ENABLED_CHARTS_NOT_ARRAY` | error | enabledChartsが配列でない |
| `CONFIG_UNKNOWN_CHART_TYPE` | error | 未登録のチャートタイプ |
| `CONFIG_DUPLICATE_ENABLED_CHARTS` | warning | enabledChartsに重複 |
| `CONFIG_EMPTY_ENABLED_CHARTS` | warning | enabledChartsが空 |
| `CONFIG_UNKNOWN_DEFAULT_CHART` | error | defaultChartが未登録 |
| `CONFIG_DEFAULT_NOT_IN_ENABLED` | error | defaultChartがenabledChartsに含まれない |
| `CONFIG_CHART_ORDER_NOT_ARRAY` | error | chartOrderが配列でない |
| `CONFIG_UNKNOWN_CHART_IN_ORDER` | warning | chartOrderに未登録のチャート |
| `CONFIG_ENABLED_NOT_IN_ORDER` | warning | enabledChartsのチャートがchartOrderにない |

#### 結果データ関連 (RESULT_*)

| コード | 重要度 | 説明 |
|--------|--------|------|
| `RESULT_NULL` | error | 結果データがnull |
| `RESULT_CLUSTERS_NOT_ARRAY` | error | clustersが配列でない |
| `RESULT_NO_CLUSTERS` | warning | clustersが空 |
| `CLUSTER_MISSING_ID` | error | クラスターにidがない |
| `CLUSTER_MISSING_LEVEL` | error | クラスターにlevelがない |
| `RESULT_ARGUMENTS_NOT_ARRAY` | error | argumentsが配列でない |

### ストリクトモード

レジストリをストリクトモードに設定すると、バリデーションエラー時に例外をスローします：

```typescript
import { chartRegistry } from "@/components/charts/plugins";

// 開発環境でストリクトモードを有効化
if (process.env.NODE_ENV === "development") {
  chartRegistry.setStrictMode(true);
}

// エラーのあるプラグインを登録しようとすると例外がスロー
chartRegistry.register(invalidPlugin); // throws Error
```

### バリデーションの使用例

```typescript
import {
  validatePlugin,
  validateVisualizationConfig,
  formatValidationResult,
  chartRegistry,
} from "@/components/charts/plugins";

// プラグインの検証
const plugin = createMyPlugin();
const pluginResult = validatePlugin(plugin);

if (!pluginResult.valid) {
  console.error("Plugin validation failed:");
  console.error(formatValidationResult(pluginResult));
}

// visualization_configの検証
const config = { enabledCharts: ["scatterAll", "unknownChart"] };
const configResult = validateVisualizationConfig(config, chartRegistry);

if (!configResult.valid) {
  console.error("Config validation failed:");
  console.error(formatValidationResult(configResult));
}
// Output:
// ✗ 1 error(s):
//   [CONFIG_UNKNOWN_CHART_TYPE] visualizationConfig.enabledCharts contains unknown chart type 'unknownChart'. Available: scatterAll, scatterDensity, treemap, hierarchyList
```

### 自動バリデーション

`ClientContainer` コンポーネントは、ロード時に自動的にバリデーションを実行し、警告をコンソールに出力します：

```typescript
// apps/public-viewer/components/report/ClientContainer.tsx
useEffect(() => {
  const resultValidation = validateResultData(result);
  if (!resultValidation.valid || resultValidation.warnings.length > 0) {
    console.warn(`Result data validation:\n${formatValidationResult(resultValidation)}`);
  }

  const configValidation = validateVisualizationConfig(result.visualizationConfig, chartRegistry);
  if (!configValidation.valid || configValidation.warnings.length > 0) {
    console.warn(`Visualization config validation:\n${formatValidationResult(configValidation)}`);
  }
}, [result]);
```

## 関連ファイル

- `apps/public-viewer/components/charts/plugins/` - プラグインシステム
- `apps/public-viewer/components/charts/plugins/validation.ts` - バリデーションシステム
- `apps/public-viewer/components/charts/` - チャートコンポーネント
- `apps/public-viewer/components/report/ClientContainer.tsx` - visualization_config読み込みとバリデーション
- `apps/public-viewer/type.ts` - 型定義（ChartType, ReportDisplayConfig）
