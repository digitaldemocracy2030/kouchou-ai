# M5 プラグインシステム改善計画（詳細版）

## 背景と前提
M5 リファクタリング後、analysis-core には分析ステップ向けのプラグイン機構が存在する。
セルフホスト環境で管理者が導入可否を判断する運用を前提に、契約・互換性・再現性を強化する。

### 前提
- セルフホスト前提で、管理者がプラグイン選定・導入を責任を持って行う。
- SaaS / マルチテナントのサンドボックス要件は想定しない。
- in-process 実行を許容する。
- まずは分析ステップのプラグインのみを対象とする。

### 目的
- 明確で安定したプラグイン契約（入出力・失敗時挙動）を定義する。
- 実行の再現性とアーティファクト追跡を担保する。
- ワークフロー（CLI / apps/api）統合を滑らかにする。
- 破壊的変更に備えた互換性方針を用意する。

### 非目的
- Marketplace、署名、審査フローの整備。
- クライアントサイドのサンドボックスやリモート実行。
- マルチテナントの権限分離。

## 現状のギャップ（改善対象）
1. ~~組み込みプラグインが `outputs/` を固定参照し、`StepContext.output_dir` を無視している。~~ ✅ Phase A で解決
2. ~~WorkflowEngine が `validate_inputs / validate_config` を呼ばないため、不足入力が見逃される。~~ ✅ Phase A で解決
3. manifest が読み込み用途止まりで、互換性・検証・依存を保証できていない。 → Phase B
4. CLI / apps/api が外部プラグイン読み込みに統合されていない。 → Phase C
5. 出力にプラグイン情報が残らず再現性が弱い。 → Phase D

## 設計方針（セルフホスト向け）
1. **契約の明示**: アーティファクト ID とファイル名の対応を固定し、IO の期待値を公開する。
2. **manifest は契約**: 互換性・依存・検証に使う必須情報として扱う。
3. **互換性運用**: セルフホストでも deprecation の猶予期間を設ける。
4. **再現性重視**: 実行結果にプラグイン ID/Version/Source を記録する。

---

# 仕様案

## 1) プラグイン契約 v1（分析ステップ）

### アーティファクト ID 一覧（現行出力に合わせる）
| artifact_id | 由来ステップ | ファイル名（既存） |
|---|---|---|
| comments | 入力 | `inputs/{input}.csv` |
| arguments | extraction | `args.csv` |
| relations | extraction | `relations.csv` |
| embeddings | embedding | `embeddings.pkl` |
| clusters | hierarchical_clustering | `hierarchical_clusters.csv` |
| initial_labels | hierarchical_initial_labelling | `hierarchical_initial_labels.csv` |
| merge_labels | hierarchical_merge_labelling | `hierarchical_merge_labels.csv` |
| overview | hierarchical_overview | `hierarchical_overview.txt` |
| result | hierarchical_aggregation | `hierarchical_result.json` |
| html | hierarchical_visualization | `index.html` |

### StepContext 拡張（提案）
`analysis_core/plugin/interface.py` に追加:
```python
@dataclass
class StepContext:
    output_dir: Path
    input_dir: Path
    dataset: str
    provider: str
    model: str
    local_llm_address: str | None = None
    user_api_key: str | None = None
    run_id: str | None = None  # 実行識別子（任意）
```

### StepOutputs.metadata（実装例）
```python
metadata = {
  "artifacts": {
    "arguments": {"path": ".../args.csv", "size_bytes": 1234, "sha256": "..."},
  },
  "plugin": {"id": "analysis.extraction", "version": "1.0.0"},
}
```

---

## 2) manifest v1（YAML）

### 必須フィールド
- `id`（不変 ID）
- `version`（semver）
- `entry`（`module:attribute`）
- `inputs` / `outputs`
- `api_version`（プラグイン API レベル）
- `requires_analysis_core`（semver 範囲）

### 任意フィールド
- `name` / `description`
- `use_llm`
- `config_schema`（JSON Schema）

### manifest 例
```yaml
id: mycompany.custom_step
version: "1.2.0"
name: "Custom Step"
description: "追加分析"
entry: plugin:custom_step_plugin
inputs: [arguments, clusters]
outputs: [custom_result]
use_llm: false
api_version: "1"
requires_analysis_core: ">=0.1.0,<0.3.0"
config_schema:
  type: object
  properties:
    threshold:
      type: number
      default: 0.5
```

---

# 実装計画（具体案）

## Phase A: 正当性と契約の強制 ✅ (2026-01-19 完了)
目的: 既存プラグインとワークフローエンジンが契約を守るようにする。

### 実装状況
M5_REFACTORING_PLAN.md の Phase 3 で以下を実装:
- ✅ 組み込みプラグイン8件で `Path("outputs")` → `ctx.output_dir` に修正
- ✅ `WorkflowEngine` に `validate_inputs()` / `validate_config()` 呼び出しを追加
- ✅ バリデーションテスト5件、output_dir回帰テスト2件を追加
- ⏭️ 共通パス解決ユーティリティ (`paths.py`) は `ctx.output_dir` 直接使用で代替
- ⏭️ Artifact メタ情報の自動付与（SHA256等）は Phase D に延期

### 変更対象
- `packages/analysis-core/src/analysis_core/steps/*.py`
- `packages/analysis-core/src/analysis_core/plugins/builtin/*.py`
- `packages/analysis-core/src/analysis_core/workflow/engine.py`
- `packages/analysis-core/src/analysis_core/core/paths.py`（新規）

### 実装案
1) **共通パス解決ユーティリティ追加**
```python
# analysis_core/core/paths.py
from pathlib import Path

def output_path(config: dict, filename: str) -> Path:
    base = Path(config.get("_output_base_dir", "outputs"))
    return base / config["output_dir"] / filename

def input_path(config: dict, filename: str) -> Path:
    base = Path(config.get("_input_base_dir", "inputs"))
    return base / filename
```
2) **steps の固定パスを置換**
例: `steps/extraction.py`
```python
path = output_path(config, "args.csv")
comments = pd.read_csv(input_path(config, f\"{config['input']}.csv\"))
```
3) **builtin プラグインが ctx を尊重**
```python
legacy_config = {...}
legacy_config["_output_base_dir"] = str(ctx.output_dir.parent)
legacy_config["_input_base_dir"] = str(ctx.input_dir)
```
4) **WorkflowEngine に検証を追加**
```python
errors = plugin.validate_inputs(inputs) + plugin.validate_config(step_config)
if errors: raise WorkflowExecutionError(...)
```
5) **Artifact メタ情報の自動付与**
`WorkflowEngine` で `StepOutputs.artifacts` を走査し SHA256 を計算し `metadata["artifacts"]` に格納。

### 完了条件
- ✅ 組み込みプラグインが固定の `outputs/` に書き込まない。
- ✅ WorkflowEngine が missing input を弾く（optional 以外）。
- ✅ missing input 検知のテストが 1 件以上。

---

## Phase B: Manifest v1 と互換性方針
目的: プラグインメタデータと互換性チェックを正式化する。

### 変更対象
- `analysis_core/plugin/manifest.py`（新規）
- `analysis_core/plugin/loader.py`
- `analysis_core/plugin/registry.py`
- `packages/analysis-core/pyproject.toml`

### 実装案
1) **manifest の型定義（pydantic）**
```python
class PluginManifest(BaseModel):
    id: str
    version: str
    entry: str
    inputs: list[str] = []
    outputs: list[str] = []
    api_version: str = "1"
    requires_analysis_core: str
    config_schema: dict[str, Any] | None = None
```
2) **互換性チェック**
- `requires_analysis_core` は `packaging.specifiers.SpecifierSet` で評価。
- `api_version` は `PLUGIN_API_VERSION` と一致必須。
3) **config_schema 検証**
- `jsonschema` を追加して `validate(instance, schema)` を実行。
4) **CLI / registry メタ情報の拡張**
- `registry.list_metadata()` で `id/version/inputs/outputs/api_version` を返す。

### 完了条件
- 不正 manifest が読み込み時に失敗する。
- 出力 JSON に plugin id / version が記録される。

---

## Phase C: ワークフローとローダ統合
目的: プラグイン実行をワークフローの正規ルートにする。

### 変更対象
- `analysis_core/__main__.py`
- `analysis_core/orchestrator.py`
- `analysis_core/workflow/loader.py`（新規、任意）
- `apps/api` の実行箇所（例: `report_launcher.py`）

### 実装案
1) **CLI 拡張**
```
--workflow <id|path>
--plugins <path>   (複数指定可)
--list-plugins
```
2) **workflow 実行時に load_all_plugins**
```python
from analysis_core.plugin import load_all_plugins
load_all_plugins(plugin_paths=parsed_paths)
```
3) **PipelineOrchestrator.run_workflow の拡張**
```python
def run_workflow(self, workflow=None, plugin_paths=None):
    load_all_plugins(plugin_paths=plugin_paths)
    ...
```
4) **apps/api 連携**
- 環境変数 `ANALYSIS_WORKFLOW` / `ANALYSIS_PLUGINS_PATH` を受け取り workflow 実行を切替。

### 完了条件
- CLI で外部プラグイン読み込み + workflow 実行が可能。
- `docs/PLUGIN_GUIDE.md` と CLI 動作が一致。

---

## Phase D: 管理者運用と再現性
目的: セルフホスト管理者が再現性を担保できる仕組みを提供する。

### 変更対象
- `analysis_core/plugin/audit.py`（新規）
- 出力 JSON 埋め込み処理（aggregation 後に追加）

### 実装案
1) **plugins.lock.json 仕様**
```json
{
  \"analysis_core_version\": \"0.1.0\",
  \"generated_at\": \"2026-01-19T00:00:00Z\",
  \"plugins\": [
    {\"id\": \"analysis.extraction\", \"version\": \"1.0.0\", \"path\": \"...\", \"sha256\": \"...\"}
  ]
}
```
2) **audit コマンド**
- `kouchou-analyze --plugins-lock write`
- `kouchou-analyze --plugins-lock check`
3) **出力メタデータに記録**
- `hierarchical_result.json` の `config` 直下に `analysis_metadata.plugins` を追加。

### 完了条件
- lock ファイルで同一構成を再現できる。

---

## Phase E: DX とテスト
目的: プラグイン開発と保守の負担を下げる。

### 変更対象
- `packages/analysis-core/tests/`
- `docs/PLUGIN_GUIDE.md`
- `tools/templates/plugin/`（新規）

### 実装案
1) **テンプレート提供**
```
tools/templates/plugin/
├── manifest.yaml
└── plugin.py
```
2) **テスト追加**
- loader の manifest 検証
- WorkflowEngine の missing input 検知
- 外部プラグイン読み込みの統合テスト
3) **トラブルシューティング強化**
- 典型的な manifest エラーと修正方法を明記。

### 完了条件
- ドキュメント通りに新規プラグインが作成できる。
- loader / workflow のテストが存在する。

---

# リスクと対策
- in-process プラグインがパイプラインを壊す可能性がある。
  - 対策: 入力検証・例外処理・optional ステップの明示。
- 組み込みステップと外部プラグインの互換性ズレ。
  - 対策: api_version と非推奨方針の導入。

# 未決事項
- workflow モードを CLI / apps/api のデフォルトにするか。
- プラグイン一覧を result JSON / status JSON のどちらに記録するか。
- 長時間ステップに対するタイムアウトや資源制限を導入するか。
