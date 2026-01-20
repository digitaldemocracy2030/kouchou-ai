# プラグイン開発ガイド

kouchou-ai には3種類のプラグインシステムがあります：

1. **入力プラグイン** - 外部サービス（YouTube、Twitter等）からデータを取得
2. **分析プラグイン** - 分析パイプラインの処理ステップをカスタマイズ
3. **可視化プラグイン** - 分析結果の表示・可視化をカスタマイズ

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

import pandas as pd
from typing import Any

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

    def fetch_data(self, source: str, **options: Any) -> pd.DataFrame:
        """データを取得してDataFrameで返す"""
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
        return pd.DataFrame([
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

`fetch_data()` は以下のカラムを持つ `pd.DataFrame` を返す必要があります：

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

参考実装として [apps/api/src/plugins/youtube.py](../apps/api/src/plugins/youtube.py) を参照してください。

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
| `analysis.embedding` | 埋め込みベクトル生成 |
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

    # 入力ファイルを読み込み
    args_path = inputs.artifacts.get("arguments")

    # 処理を実行
    # ...

    # 結果を保存
    output_path = ctx.output_dir / "custom_result.csv"
    # result_df.to_csv(output_path, index=False)

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

```bash
# プラグインディレクトリを環境変数で指定
export ANALYSIS_PLUGINS_PATH=/path/to/plugins:/another/path

# パイプライン実行時に自動的に読み込まれる
python -m analysis_core config.json
```

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
    from analysis_core.services.llm import request_to_chat_ai

    # プロンプトを取得（configから、またはデフォルト）
    prompt = config.get("prompt", "Analyze the following...")
    model = config.get("model", ctx.model)

    # LLMリクエスト
    response = request_to_chat_ai(
        messages=[{"role": "user", "content": prompt}],
        model=model,
        provider=ctx.provider,
    )

    # トークン使用量を記録
    return StepOutputs(
        artifacts={"analysis_result": output_path},
        token_usage=response.get("total_tokens", 0),
        token_input=response.get("prompt_tokens", 0),
        token_output=response.get("completion_tokens", 0),
    )
```

## テスト

プラグインのテスト例：

```python
import pytest
from pathlib import Path
from analysis_core.plugin import StepContext, StepInputs

def test_custom_plugin():
    # テスト用コンテキスト
    ctx = StepContext(
        output_dir=Path("/tmp/test_output"),
        input_dir=Path("/tmp/test_input"),
        dataset="test",
        provider="openai",
        model="gpt-4o-mini",
    )

    # テスト用入力
    inputs = StepInputs(
        artifacts={"arguments": Path("/tmp/test_input/args.csv")},
    )

    # プラグイン実行
    result = custom_step_plugin(ctx, inputs, {"threshold": 0.5})

    # 検証
    assert result.artifacts.get("custom_result") is not None
    assert result.artifacts["custom_result"].exists()
```

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
- レポート表示形式のカスタマイズ
- 外部ダッシュボードとの連携

## ステータス

> **Note**: 可視化プラグインシステムは現在設計段階です。
> 詳細なAPIとドキュメントは今後追加予定です。

## 想定されるユースケース

1. **カスタムチャートタイプ**
   - 階層クラスタリング結果の独自可視化
   - センチメント分析のヒートマップ
   - 時系列トレンド分析

2. **レポートテンプレート**
   - 組織固有のブランディング
   - 多言語対応
   - アクセシビリティ対応

3. **外部連携**
   - BIツール（Tableau、Power BI等）へのエクスポート
   - データポータルとの統合

## 関連ファイル

現在の可視化実装は以下にあります：

- `apps/public-viewer/components/charts/` - グラフコンポーネント
- `apps/public-viewer/components/report/` - レポート表示コンポーネント
- `apps/api/broadlistening/pipeline/steps/hierarchical_visualization.py` - HTML生成
