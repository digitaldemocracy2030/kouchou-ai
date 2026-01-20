# 作業ログ

## 2026-01-19

### Phase 0: 現状把握・棚卸し

#### 実施内容
1. エントリポイントとビルド経路の調査
   - compose.yaml: 5サービス（api, client, client-admin, client-static-build, ollama）
   - Makefile: ローカル開発とAzure関連コマンド
   - scripts/: fetch_reports.py, upload_reports_to_azure.py, assign_storage_role.sh

2. パイプライン構造の調査
   - hierarchical_main.py: メインオーケストレーター（8ステップ）
   - report_launcher.py: API からの呼び出し元
   - hierarchical_specs.json: ステップ定義

3. 結果JSON構造の確認
   - hierarchical_result.json の構造を確認
   - arguments, clusters, comments, propertyMap, translations, overview, config, comment_num

4. client/admin間の重複調査
   - 型定義の重複: Meta, ReportVisibility, Report, Result, Argument, Cluster, Comments, Config
   - UIコンポーネントの重複: button, checkbox, dialog 等 12ファイル

5. ハードコード箇所の特定
   - ProgressSteps.tsx: ステップ名の固定配列
   - SelectChartButton.tsx: チャート種別の固定配列

#### 作成ファイル
- docs/refactoring/phase0_investigation.md - 調査結果ドキュメント

#### 次のステップ
Phase 1: リポジトリ構成の整理（apps/ と packages/ 導入）

### Phase 1: リポジトリ構成の整理

#### 実施内容
1. ディレクトリ移動
   - server/ → apps/api/
   - client/ → apps/public-viewer/（名前変更も実施）
   - client-admin/ → apps/admin/
   - client-static-build/ → apps/static-site-builder/（名前変更も実施）
   - scripts/ → tools/scripts/
   - experimental/ → experiments/

2. 設定ファイル更新
   - compose.yaml: 新しいパスに更新
   - Makefile: 全てのパス参照を更新
   - GitHub Actions ワークフロー更新:
     - server-pytest.yml
     - client-build.yml
     - client-admin-build.yml
     - client-jest.yml
     - client-admin-jest.yml
     - ruff-check.yml
     - e2e-tests.yml
     - azure-deploy.yml

3. Dockerfile更新
   - apps/static-site-builder/Dockerfile: 新しいパスに更新

4. ドキュメント更新
   - CLAUDE.md: 新しいパスに更新
   - docs/refactoring/phase0_investigation.md: 新構造を反映

#### 作成ファイル
- docs/refactoring/naming_convention.md - 命名規約と対応表ドキュメント

#### 命名規約（新規）
| 旧名 | 新名 | 説明 |
|-----|-----|------|
| server/ | apps/api/ | バックエンドAPI |
| client/ | apps/public-viewer/ | 公開閲覧用フロントエンド |
| client-admin/ | apps/admin/ | 管理画面 |
| client-static-build/ | apps/static-site-builder/ | 静的サイト生成 |

#### 次のステップ
Phase 1続き: packages/ ディレクトリ作成、ワークスペース設定

### Phase 1 続き: Docker/Azureサービス名の統一

#### 背景
ディレクトリ名（例: `apps/public-viewer/`）とDockerサービス名（例: `client`）が異なっていたため、不要な複雑さが生じていた。新規ユーザーにとっての理解しやすさを優先し、サービス名をディレクトリ名に統一することを決定。

#### 実施内容

1. compose.yaml 更新
   - サービス名変更:
     - `client` → `public-viewer`
     - `client-admin` → `admin`
     - `client-static-build` → `static-site-builder`
   - YAMLアンカー名変更:
     - `x-client-common` → `x-frontend-common`
     - `x-client-build-args` → `x-frontend-build-args`

2. Makefile 更新
   - 全てのDockerイメージタグを新サービス名に変更
   - 全てのAzure Container App参照を新サービス名に変更
   - Makeターゲット名変更:
     - `azure-logs-client` → `azure-logs-public-viewer`
     - `azure-logs-client-static-build` → `azure-logs-static-site-builder`
     - `azure-restart-client` → `azure-restart-public-viewer`
     - `azure-restart-client-static-build` → `azure-restart-static-site-builder`
     - `azure-fix-client-admin` → `azure-fix-admin`

3. Azure テンプレートファイル更新
   - ファイル名変更:
     - `client-health-probe.yaml` → `public-viewer-health-probe.yaml`
     - `client-admin-health-probe.yaml` → `admin-health-probe.yaml`
     - `client-static-build-health-probe.yaml` → `static-site-builder-health-probe.yaml`
     - `client-pull-policy.yaml` → `public-viewer-pull-policy.yaml`
     - `client-admin-pull-policy.yaml` → `admin-pull-policy.yaml`
     - `client-static-build-pull-policy.yaml` → `static-site-builder-pull-policy.yaml`
   - テンプレート内のサービス名・イメージ名を更新

4. GitHub Actions ワークフロー更新
   - azure-deploy.yml: 全てのサービス名・イメージ名を新名称に変更

5. ドキュメント更新
   - docs/refactoring/naming_convention.md: サービス名統一を反映

#### サービス名対応表（最終）
| ディレクトリ | Docker サービス名 | Azure Container App 名 |
|-------------|------------------|------------------------|
| `apps/api/` | `api` | `api` |
| `apps/public-viewer/` | `public-viewer` | `public-viewer` |
| `apps/admin/` | `admin` | `admin` |
| `apps/static-site-builder/` | `static-site-builder` | `static-site-builder` |

#### 次のステップ
Phase 1続き: packages/ ディレクトリ作成、ワークスペース設定

### Phase 1 続き: packages/ ディレクトリ作成とpnpmワークスペース設定

#### 実施内容

1. pnpmワークスペース設定
   - pnpm-workspace.yaml 作成
   - ルート package.json 更新（packageManager, workspaces対応スクリプト）
   - .npmrc 作成（shamefully-hoist, strict-peer-dependencies）

2. 共通パッケージ作成
   - packages/report-schema/ 作成
     - TypeScript型定義を統合
     - Meta, ReportVisibility, Report, Argument, Cluster, Comments, Result, Config等
     - apps/public-viewer/type.ts と apps/admin/type.d.ts から統合

3. パッケージ名の統一
   - apps/public-viewer: kouchou-ai-client → @kouchou-ai/public-viewer
   - apps/admin: kouchou-ai-client-admin → @kouchou-ai/admin
   - apps/static-site-builder: client-static-build → @kouchou-ai/static-site-builder
   - test/e2e: kouchou-ai-e2e-tests → @kouchou-ai/e2e-tests

4. ワークスペース依存関係追加
   - apps/public-viewer に @kouchou-ai/report-schema: workspace:* 追加
   - apps/admin に @kouchou-ai/report-schema: workspace:* 追加

#### 作成ファイル
- pnpm-workspace.yaml
- .npmrc
- packages/report-schema/package.json
- packages/report-schema/tsconfig.json
- packages/report-schema/src/index.ts

#### テスト実行結果

pnpmワークスペース設定後の動作確認:

| テスト | コマンド | 結果 |
|--------|----------|------|
| public-viewer Jest | `pnpm --filter @kouchou-ai/public-viewer test` | ✅ 5 passed |
| admin Jest | `pnpm --filter @kouchou-ai/admin test` | ✅ 92 passed |
| API pytest | `cd apps/api && rye run pytest tests/` | ✅ 135 passed, 5 skipped |
| report-schema build | `pnpm --filter @kouchou-ai/report-schema build` | ✅ 成功 |

#### 追加の整理
- 古いnpm lockfileを削除（apps/*/package-lock.json）
- packages/report-schema/biome.json追加（dist/を除外）

#### Phase 1 完了コミット履歴
```
5af9902 chore: lockfile整理とbiome設定追加
8981584 Phase 1 続き: pnpmワークスペース設定と@kouchou-ai/report-schemaパッケージ作成
557cf0f Phase 1 続き: Docker/Azureサービス名をディレクトリ名に統一
bef15ac Phase 1: Reorganize repository structure with clearer directory naming
```

#### 次のステップ
- Phase 2: Analysis Core 抽出

### Phase 2: Analysis Core 抽出（開始）

#### 現状のパイプライン調査結果
- 場所: `apps/api/broadlistening/pipeline/` (約10,080 LOC)
- メインオーケストレーター: `hierarchical_main.py` (77 LOC)
- コアユーティリティ: `hierarchical_utils.py` (327 LOC), `utils.py` (353 LOC)
- 8つのステップ: extraction, embedding, clustering, labelling×2, overview, aggregation, visualization
- サービス: `llm.py` (850+ LOC), `parse_json_list.py` (114 LOC)
- エントリポイント: CLI (`hierarchical_main.py`) と API (`report_launcher.py`)

#### 実施内容
1. パッケージ構造作成
   ```
   packages/analysis-core/
   ├── pyproject.toml
   ├── README.md
   ├── src/analysis_core/
   │   ├── __init__.py
   │   ├── __main__.py      # CLIエントリ
   │   ├── config.py        # 設定管理
   │   ├── orchestrator.py  # パイプライン実行制御
   │   ├── steps/           # ステップ（未実装）
   │   ├── services/        # サービス（未実装）
   │   ├── core/            # コアユーティリティ（未実装）
   │   └── specs/
   │       └── hierarchical_specs.json
   └── tests/
       └── test_config.py
   ```

2. 基本モジュール作成
   - `PipelineConfig`: 設定管理クラス
   - `PipelineOrchestrator`: パイプライン実行制御クラス（スタブ）
   - CLIエントリポイント（スタブ）

### Phase 2: Analysis Core 抽出（続き）

#### 実施内容

1. コアユーティリティ移行
   - `core/orchestration.py`: hierarchical_utils.pyからオーケストレーション関数を移行
     - `load_specs()`, `get_specs()`, `validate_config()`, `decide_what_to_run()`
     - `update_status()`, `update_progress()`, `run_step()`, `termination()`
     - ハードコードされたPIPELINE_DIR依存を削除、設定可能に
   - `core/utils.py`: プロンプト解析ユーティリティを移行
     - `typed_message()`, `messages()`, `format_token_count()`, `estimate_tokens()`, `chunk_text()`
   - `core/__init__.py`: エクスポート設定

2. サービス移行
   - `services/llm.py`: LLMサービス（OpenAI, Azure, Gemini, OpenRouter, Local対応）
     - DOTENV_PATHのハードコード参照を修正
   - `services/parse_json_list.py`: JSON解析ユーティリティ
   - `services/__init__.py`: エクスポート設定

3. ステップ移行（全8ステップ）
   - `steps/extraction.py`: 意見抽出ステップ
   - `steps/embedding.py`: 埋め込みベクトル生成ステップ
   - `steps/hierarchical_clustering.py`: 階層クラスタリングステップ
   - `steps/hierarchical_initial_labelling.py`: 初期ラベリングステップ
   - `steps/hierarchical_merge_labelling.py`: マージラベリングステップ
   - `steps/hierarchical_overview.py`: 概要生成ステップ
   - `steps/hierarchical_aggregation.py`: 結果集約ステップ
     - pipeline_dir設定を引数化
   - `steps/hierarchical_visualization.py`: 可視化ステップ
   - `steps/__init__.py`: エクスポート設定

4. テストファイル作成
   - `tests/test_imports.py`: パッケージインポートテスト
     - コアモジュール、サービス、ステップ、設定の全インポートをテスト

#### インポートパス変更
```python
# 旧
from services.llm import request_to_chat_ai
from utils import update_progress

# 新
from analysis_core.services.llm import request_to_chat_ai
from analysis_core.core import update_progress
```

#### 現在の構造
```
packages/analysis-core/
├── pyproject.toml
├── README.md
├── src/analysis_core/
│   ├── __init__.py
│   ├── __main__.py
│   ├── config.py
│   ├── orchestrator.py
│   ├── core/
│   │   ├── __init__.py
│   │   ├── orchestration.py
│   │   └── utils.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── llm.py
│   │   └── parse_json_list.py
│   ├── steps/
│   │   ├── __init__.py
│   │   ├── extraction.py
│   │   ├── embedding.py
│   │   ├── hierarchical_clustering.py
│   │   ├── hierarchical_initial_labelling.py
│   │   ├── hierarchical_merge_labelling.py
│   │   ├── hierarchical_overview.py
│   │   ├── hierarchical_aggregation.py
│   │   └── hierarchical_visualization.py
│   └── specs/
│       └── hierarchical_specs.json
└── tests/
    ├── test_config.py
    └── test_imports.py
```

#### テスト実行結果

Python 3.12.8をpyenvでインストールし、パッケージテストを実行:

```bash
cd packages/analysis-core
~/.pyenv/versions/3.12.8/bin/python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest tests/ -v
```

結果: **20 passed** (2.51s)
- test_config.py: 4 passed
- test_imports.py: 16 passed

修正した問題:
- `parse_json_list` → `parse_response` に関数名を修正

#### コミット履歴
```
9aae04d9 fix: Correct parse_response export and add .gitignore
cf15e0d  docs: Add Python 3.12 requirement to README
01df36a  Phase 2: Migrate core utilities, services, and steps to analysis-core package
48cf3c1  Phase 2: Create analysis-core package structure
```

#### 次のステップ
- apps/apiからの呼び出しを新パッケージに切り替え
- 統合テスト

### Phase 2.5: PyPIパッケージ化（計画策定）

#### 現状分析

Phase 2 で移行済みの内容:
- パッケージ構造 (`packages/analysis-core/`)
- 全ステップ (8ステップ)
- コアユーティリティ (`core/orchestration.py`, `core/utils.py`)
- サービス (`services/llm.py`, `services/parse_json_list.py`)

未完了の項目:
1. `orchestrator.py` の `run()` メソッドがスタブ実装
2. `__main__.py` がレガシーへのリダイレクトのみ
3. `hierarchical_utils.py` の `initialization()` 関数が未移行
4. `apps/api` は依然として `hierarchical_main.py` を subprocess で呼び出し

#### 作成ファイル
- `docs/refactoring/phase2_5_plan.md` - Phase 2.5 詳細計画

#### タスク一覧

| Task | 内容 | 見積もり |
|------|------|----------|
| 2.5.1 | initialization 関数の移行 | 1-2時間 |
| 2.5.2 | PipelineOrchestrator の完成 | 2-3時間 |
| 2.5.3 | CLI実装の完成 | 1時間 |
| 2.5.4 | プロンプトファイルの移行 | 30分 |
| 2.5.5 | apps/api からの呼び出し切り替え | 1-2時間 |
| 2.5.6 | 依存関係の整理（オプション） | 1時間 |
| 2.5.7 | テストの拡充 | 2-3時間 |
| 2.5.8 | バージョニングとリリース準備 | 1時間 |

#### 方針決定
- apps/api からの呼び出し: **subprocess 維持（CLI呼び出し）**
  - 理由: 既存動作維持、analysis-core の独立性保持、段階移行可能

#### 次のステップ
- Task 2.5.1 から順に実施

### Phase 3: 分析プラグイン化（計画策定）

#### 作成ファイル
- `docs/refactoring/phase3_plan.md` - Phase 3 詳細計画

#### 目標
- 既存8ステップをプラグインアーキテクチャに変換
- ワークフロー定義で手順を制御可能に
- 外部プラグイン読み込み機構

#### タスク一覧

| Task | 内容 | 見積もり |
|------|------|----------|
| 3.1 | プラグインインターフェース定義 | 2-3時間 |
| 3.2 | プラグインレジストリ実装 | 1-2時間 |
| 3.3 | 既存ステップのプラグイン化 | 4-6時間 |
| 3.4 | ワークフローエンジン実装 | 3-4時間 |
| 3.5 | デフォルトワークフロー定義 | 1時間 |
| 3.6 | 互換レイヤー実装 | 1-2時間 |
| 3.7 | Orchestrator対応 | 2-3時間 |
| 3.8 | 外部プラグイン読み込み | 2-3時間 |
| 3.9 | Analysis画面互換性 | 1-2時間 |

#### アーキテクチャ概要

```
PluginRegistry (プラグイン登録・管理)
    ↓
WorkflowEngine (ワークフロー実行)
    ↓
StepPlugin (統一インターフェース)
    - StepContext: 実行環境
    - StepInputs: 入力アーティファクト
    - StepOutputs: 出力アーティファクト
```

#### 段階的実施
- Phase 3a: プラグイン基盤（3.1〜3.3）
- Phase 3b: ワークフロー基盤（3.4〜3.7）
- Phase 3c: 拡張機能（3.8〜3.9）

### Phase 2.5.1: initialization関数の移行（完了）

#### 実施内容
1. `core/orchestration.py` に `initialization()` 関数を追加
   - 設定ファイル読み込み
   - 設定バリデーション
   - 前回実行ステータス確認
   - ステップ設定のデフォルト値設定
   - 出力ディレクトリ作成
   - 実行プラン決定

2. 設定可能なパラメータ:
   - `config_path`: 設定JSONファイルパス
   - `force`: 強制再実行フラグ
   - `only`: 特定ステップのみ実行
   - `skip_interaction`: インタラクティブ確認スキップ
   - `without_html`: HTML出力スキップ
   - `output_base_dir`: 出力ベースディレクトリ
   - `input_base_dir`: 入力ベースディレクトリ
   - `specs_path`: ステップ仕様JSONパス
   - `steps_module`: ソースコード取得用モジュール

3. エクスポート追加
   - `core/__init__.py` に `initialization` を追加

4. テスト追加
   - `tests/test_orchestration.py` 作成（11テスト）

#### テスト結果
- 31 passed (test_config: 4, test_imports: 16, test_orchestration: 11)

### Phase 2.5.2: PipelineOrchestrator完成

#### 実施内容
1. `orchestrator.py` を完全に書き直し
   - `DEFAULT_STEP_FUNCTIONS` 辞書: 8ステップへの関数マッピング
   - `StepResult`: ステップ実行結果のdataclass
   - `PipelineResult`: パイプライン全体の実行結果dataclass
   - `PipelineOrchestrator.from_config()`: configファイルからの初期化
   - `PipelineOrchestrator.run()`: パイプライン実行メソッド
   - `register_step()`: カスタムステップ登録
   - `get_plan()`, `get_status()`: 実行計画・ステータス取得

2. テスト追加
   - `test_orchestration.py` に5つのPipelineOrchestratorテストを追加

#### テスト結果
- 36 passed

### Phase 2.5.3: CLI実装完成

#### 実施内容
1. `__main__.py` を完全に書き直し
   - `PipelineOrchestrator.from_config()` を使用
   - `--output-dir`, `--input-dir` 引数追加
   - `--dry-run` 引数追加（実行せずにプラン表示）
   - 実行結果のサマリー表示
   - ステップごとの実行時間・エラー表示

2. CLIテスト作成
   - `tests/test_cli.py` 作成
   - `test_cli_help`: ヘルプ表示テスト
   - `test_cli_version`: バージョン表示テスト
   - `test_cli_missing_config`: 設定ファイル不在テスト
   - `test_cli_dry_run`: dry-runテスト

#### テスト結果
- 40 passed (test_cli: 4, test_config: 4, test_imports: 16, test_orchestration: 16)

### Phase 2.5.4: デフォルトプロンプト移行

~~プロンプトはAPIから`report_input.prompt`として設定に含まれて渡されるため、analysis-coreにプロンプトファイルを含める必要はない。CLIでプロンプトなしで使う場合のフォールバックは将来必要に応じて追加。~~

**修正**: Web版ではデフォルトプロンプトが`apps/admin/app/create/`内に定義されており、ユーザがカスタマイズしない限りそれがAPIに渡される。CLI版でも同様に「特にカスタマイズしていない限りデフォルトプロンプトが使われる」べき。

#### 実施内容
1. デフォルトプロンプト調査
   - `apps/admin/app/create/extractionPrompt.ts` - 意見抽出プロンプト
   - `apps/admin/app/create/initialLabellingPrompt.ts` - 初期ラベリングプロンプト
   - `apps/admin/app/create/mergeLabellingPrompt.ts` - 統合ラベリングプロンプト
   - `apps/admin/app/create/overviewPrompt.ts` - 概要生成プロンプト

2. デフォルトプロンプトモジュール作成
   - `packages/analysis-core/src/analysis_core/prompts/__init__.py`
   - 4つのプロンプト定数（EXTRACTION_PROMPT, INITIAL_LABELLING_PROMPT, MERGE_LABELLING_PROMPT, OVERVIEW_PROMPT）
   - `DEFAULT_PROMPTS` 辞書（ステップ名→プロンプト）
   - `get_default_prompt()` 関数

3. `initialization` 関数更新
   - `core/orchestration.py` に `use_llm: true` のステップにデフォルトプロンプトを設定する処理を追加
   - カスタムプロンプトが設定されている場合はそれを優先

4. テスト追加
   - `tests/test_prompts.py` 作成（12テスト）
   - プロンプト定義テスト
   - `get_default_prompt()` テスト
   - 設定初期化時のデフォルトプロンプト適用テスト
   - カスタムプロンプト保持テスト

#### 変更ファイル
- `packages/analysis-core/src/analysis_core/prompts/__init__.py` (新規)
- `packages/analysis-core/src/analysis_core/core/orchestration.py` (更新)
- `packages/analysis-core/tests/test_prompts.py` (新規)

#### テスト結果
- analysis-core: 56 passed (test_cli: 4, test_config: 4, test_imports: 16, test_integration: 4, test_orchestration: 16, test_prompts: 12)

### Phase 2.5.5: apps/api統合

#### 実施内容
1. `report_launcher.py` を更新
   - `launch_report_generation()`: `python -m analysis_core` コマンドに変更
   - `execute_aggregation()`: 同様に更新
   - `--output-dir`, `--input-dir` 引数を追加

2. `pyproject.toml` 更新
   - コメントで analysis-core の依存関係を説明
   - subprocess呼び出しのため直接依存は不要

3. `Dockerfile` 更新
   - buildコンテキストをルートレベルに変更
   - `packages/analysis-core` をコピー・インストール
   - 依存関係の順序を調整

4. `compose.yaml` 更新
   - API サービスの context を `.` に変更

#### 変更ファイル
- `apps/api/src/services/report_launcher.py`
- `apps/api/pyproject.toml`
- `apps/api/Dockerfile`
- `compose.yaml`

#### テスト結果
- apps/api pytest: 134 passed, 1 failed（既存のテストセットアップ問題）, 5 skipped

#### 追加対応: ルートレベル.dockerignore作成
compose.yamlでAPIのbuildコンテキストがルートレベル(`.`)に変更されたため、不要なファイルがDockerビルドに含まれないよう`.dockerignore`を作成。

除外対象:
- `.git/`, `.idea/`, `.vscode/` - バージョン管理・IDE
- `**/tests/`, `**/__tests__/`, `test/` - テストファイル
- `**/.venv/`, `node_modules/` - 依存関係
- `*.md` (README.md以外), `docs/` - ドキュメント
- `experiments/`, `tools/`, `utils/` - 開発ツール
- パイプラインのinputs/outputs/configsディレクトリ

### Phase 2.5.7: テスト拡充

#### 実施内容
1. `tests/test_integration.py` 追加
   - `test_run_with_mocked_steps`: モック化されたステップの順序実行テスト
   - `test_run_handles_step_failure`: ステップ失敗時のエラーハンドリングテスト
   - `test_full_plan_execution`: 全8ステップの実行計画テスト
   - `test_status_tracking`: ステータス追跡テスト

#### テスト結果
- analysis-core: 44 passed (test_cli: 4, test_config: 4, test_imports: 16, test_integration: 4, test_orchestration: 16)

### Dockerビルド検証と修正

#### 問題
1. ルートレベルの`.dockerignore`が存在せず、ビルドコンテキストが最適化されていなかった
2. `umap-learn`が古い`numba`/`llvmlite`を解決し、Python 3.12非対応でビルド失敗

#### 解決
1. `.dockerignore` をルートレベルに作成
   - テスト、ドキュメント、開発ツールを除外
   - ビルドキャッシュ効率を改善

2. `packages/analysis-core/pyproject.toml` に `numba>=0.59.0` を追加
   - Python 3.12対応のnumbaを強制

#### 検証結果
- analysis-core テスト: 56 passed ✅
- Dockerビルド: 成功 ✅

#### コミット履歴
```
83beab08 fix(analysis-core): Add numba>=0.59.0 for Python 3.12 compatibility
f620b556 chore: Add root-level .dockerignore for optimized builds
87bb7c05 feat(analysis-core): Add default prompts for pipeline steps
```

### Phase 3a/3b: プラグインアーキテクチャ実装（完了）

#### 実施内容

1. **Task 3.1: プラグインインターフェース定義**
   - `plugin/interface.py`: `StepContext`, `StepInputs`, `StepOutputs`, `PluginMetadata`, `AnalysisStepPlugin`
   - 抽象基底クラスによるプラグイン規約定義

2. **Task 3.2: プラグインレジストリ実装**
   - `plugin/registry.py`: `PluginRegistry` クラス
   - `get_registry()` グローバルレジストリ関数
   - 組み込みプラグインの自動登録機構

3. **Task 3.3: 既存ステップのプラグイン化（8ステップ）**
   - `plugins/builtin/extraction.py`
   - `plugins/builtin/embedding.py`
   - `plugins/builtin/hierarchical_clustering.py`
   - `plugins/builtin/hierarchical_initial_labelling.py`
   - `plugins/builtin/hierarchical_merge_labelling.py`
   - `plugins/builtin/hierarchical_overview.py`
   - `plugins/builtin/hierarchical_aggregation.py`
   - `plugins/builtin/hierarchical_visualization.py`
   - 各プラグインは既存のステップ関数をラップ

4. **Task 3.4: ワークフローエンジン実装**
   - `workflow/definition.py`: `WorkflowStep`, `WorkflowDefinition`, `StepResult`, `WorkflowResult`
   - `workflow/resolver.py`: トポロジカルソート（Kahnのアルゴリズム）による依存解決
   - `workflow/engine.py`: `WorkflowEngine` クラス

5. **Task 3.5: デフォルトワークフロー定義**
   - `workflows/hierarchical_default.py`: `HIERARCHICAL_DEFAULT_WORKFLOW`
   - `create_hierarchical_workflow()` 関数（visualization on/off 対応）

6. **Task 3.6: 互換レイヤー実装**
   - `compat/config_converter.py`: `normalize_config()`, `convert_legacy_config()`, `create_step_context_from_config()`
   - デフォルトプロンプトの自動補完

7. **Task 3.7: Orchestrator のワークフロー対応**
   - `orchestrator.py`: `from_dict()` クラスメソッド、`run_workflow()` メソッド追加
   - `__init__.py`: `PipelineResult`, `StepResult` エクスポート追加

#### 構造
```
packages/analysis-core/src/analysis_core/
├── plugin/
│   ├── __init__.py
│   ├── interface.py
│   ├── decorator.py
│   └── registry.py
├── plugins/
│   └── builtin/
│       ├── __init__.py
│       └── (8つのプラグイン)
├── workflow/
│   ├── __init__.py
│   ├── definition.py
│   ├── engine.py
│   └── resolver.py
├── workflows/
│   ├── __init__.py
│   └── hierarchical_default.py
└── compat/
    ├── __init__.py
    └── config_converter.py
```

#### コミット
```
cf1e5596 feat(analysis-core): Add plugin architecture for pipeline steps (Phase 3)
```

### Phase 3c: 拡張機能

#### Task 3.8: 外部プラグイン読み込み機構

**実施内容**:
1. `plugin/loader.py` 作成
   - `PluginLoadError` 例外クラス
   - `PluginManifest` データクラス（manifest.yamlの解析）
   - `LoadedPlugin` データクラス（読み込み済みプラグイン情報）
   - `load_manifest()` - manifest.yaml読み込み
   - `load_plugin_module()` - Pythonモジュールからプラグイン読み込み
   - `load_plugin_from_directory()` - ディレクトリからプラグイン読み込み
   - `load_plugins_from_directory()` - 複数プラグイン一括読み込み
   - `discover_plugin_directories()` - プラグインディレクトリ自動検出
   - `load_all_plugins()` - 組み込み＋外部プラグイン一括読み込み

2. `plugin/__init__.py` 更新
   - ローダー関数のエクスポート追加

3. `pyproject.toml` 更新
   - `pyyaml>=6.0.0` 依存関係追加

4. テスト追加
   - `tests/test_loader.py` - 16テスト

**プラグインディレクトリ構造**:
```
plugins/analysis/
├── my-custom-step/
│   ├── manifest.yaml
│   └── plugin.py
```

**テスト結果**: 83 passed

#### Task 3.9: Analysis画面の互換性維持

**実施内容**:
1. `compat/config_converter.py` 更新
   - `_get_step_source_codes()` 関数追加
   - `normalize_config()` に `include_source_code` パラメータ追加
   - 各ステップに `source_code` を自動追加（Analysis画面互換）

2. テスト追加
   - `tests/test_compat.py` - 11テスト
     - `source_code` が全ステップに含まれることを検証
     - `source_code` 追加のオプトアウト機能

**Analysis画面が期待するconfig構造**:
- `result.config.plan` - 実行計画（from_dict()で設定）
- `result.config.<step>.source_code` - ステップのソースコード
- `result.config.<step>.prompt` - ステップのプロンプト
- `result.config.<step>.model` - 使用モデル

**テスト結果**: 83 passed

#### コミット
```
bebc1b23 feat(analysis-core): Add external plugin loading and Analysis screen compatibility (Phase 3c)
```

### Phase 3 完了

Phase 3 の全タスク（3.1〜3.9）が完了。analysis-core パッケージに以下の機能を追加:
- プラグインアーキテクチャ（interface, registry, decorator）
- 8つの組み込みプラグイン
- ワークフローエンジン（依存解決、実行制御）
- 外部プラグイン読み込み機構
- Analysis画面との互換性維持（source_code, plan）

次のステップ: Phase 4（API & Schema 更新）

### バグ修正: 組み込みプラグインの output_dir パス問題

#### 問題
組み込みプラグインが `StepContext.output_dir` を無視して `Path("outputs") / ctx.dataset` をハードコードしていた。これにより、`output_base_dir` を変更した実行や外部プラグイン連携時に、アーティファクトパスが不整合になる問題があった。

#### 影響ファイル（8ファイル）
- `plugins/builtin/extraction.py`
- `plugins/builtin/embedding.py`
- `plugins/builtin/hierarchical_clustering.py`
- `plugins/builtin/hierarchical_initial_labelling.py`
- `plugins/builtin/hierarchical_merge_labelling.py`
- `plugins/builtin/hierarchical_overview.py`
- `plugins/builtin/hierarchical_aggregation.py`
- `plugins/builtin/hierarchical_visualization.py`

#### 修正内容
- `Path("outputs") / ctx.dataset` → `ctx.output_dir` に変更
- 未使用となった `from pathlib import Path` インポートを削除
- ruff による未使用 `PluginMetadata` インポートの自動削除

#### テスト結果
- 83 passed ✅

### バグ修正: WorkflowEngine のバリデーション不足

#### 問題
`WorkflowEngine` が `plugin.validate_inputs()` / `plugin.validate_config()` を呼ばず、必須入力が欠けても検知しなかった。依存切れが「成功扱い」になりうるため、誤った出力やデバッグ困難が残る問題があった。

#### 修正内容
`workflow/engine.py` の `run()` メソッドで、`plugin.run()` を呼ぶ前にバリデーションを追加:
- `plugin.validate_inputs(inputs)` - 必須入力アーティファクトの存在確認
- `plugin.validate_config(step_config)` - 設定の妥当性確認

バリデーションエラー時の動作:
- 必須ステップ: ワークフロー停止、`result.success = False`
- オプションステップ: スキップして継続、`skipped=True`

#### テスト追加
`tests/test_workflow_engine.py` (5テスト):
- `test_validates_missing_inputs`: 必須入力が欠けた場合のバリデーション失敗
- `test_validates_config`: カスタム設定バリデーションの呼び出し
- `test_optional_step_validation_failure_continues`: オプションステップ失敗時の継続
- `test_valid_inputs_passes_validation`: 有効入力時の正常実行
- `test_validation_stops_workflow_early`: バリデーション失敗時の早期停止

#### テスト結果
- 88 passed ✅ (83 + 5 新規)

### Phase 3 既知の課題の整理

以下の2件は `run_workflow()` がWebapp経路に統合される Phase 5以降で対応することを決定し、M5_REFACTORING_PLAN.md に記録:

1. 外部プラグイン読み込みが `run_workflow()` に未統合
2. `run_workflow()` 経由での plan 生成未対応

理由: 現在のプロダクション経路（apps/api）は `run()` を使用しており問題なし。CLI/PyPI配布が主目的であり、Webapp側のカスタマイズは優先度低

### output_dir 回帰テスト追加

`test_workflow_engine.py` に `TestWorkflowEngineOutputDir` クラスを追加:
- `test_plugin_uses_ctx_output_dir_not_hardcoded_path`: カスタム output_dir が使われ、`Path("outputs")` がハードコードされていないことを確認
- `test_multiple_steps_share_output_dir`: 複数ステップが同じ output_dir に書き込むことを確認

テスト結果: 90 passed ✅ (88 + 2 新規)

M5_REFACTORING_PLAN.md の Phase 5 に繰越課題3件を追記:
- 外部プラグイン読み込み統合
- plan 生成実装
- 統合テスト

### Phase 3 検証: Analysis画面互換性

`run()` 経路（プロダクション経路）で plan/source_code/prompt が正しく生成されることを確認:
- plan: 8 steps ✅ (keys: step, run, reason)
- extraction.source_code: ✅
- extraction.prompt: ✅
- hierarchical_initial_labelling.source_code: ✅
- hierarchical_initial_labelling.prompt: ✅

apps/api テスト: 135 passed ✅
Docker ビルド: 成功 ✅

### ドキュメント整理

`packages/analysis-core/docs/PLUGIN_GUIDE.md` → `docs/PLUGIN_GUIDE.md` に移動
（深い位置のドキュメントは発見されにくいため）

### Phase 4: API & Schema 更新（基本実装）

#### 実施内容

1. **packages/report-schema に ReportDisplayConfig 型を追加**
   - `ChartType`: "scatterAll" | "scatterDensity" | "treemap"
   - `ScatterDensityParams`: maxDensity, minValue
   - `DisplayParams`: showClusterLabels, scatterDensity
   - `ReportDisplayConfig`: version, enabledCharts, defaultChart, chartOrder, params, updatedAt, updatedBy
   - `DEFAULT_REPORT_DISPLAY_CONFIG`: デフォルト設定値
   - 注: 既存の `VisualizationConfig` はパイプラインステップ用のため、新型名 `ReportDisplayConfig` を使用

2. **apps/api/src/schemas/visualization_config.py を作成**
   - pydantic モデルで TypeScript 型と同等の構造を定義
   - `SchemaBaseModel` を使用し camelCase alias を自動生成

3. **/reports/{slug} API を更新**
   - `visualization_config.json` が存在する場合、レスポンスに `visualizationConfig` としてマージ
   - ファイルが存在しない場合は追加なし（既存挙動を維持）

4. **client/admin の型定義を更新**
   - `apps/public-viewer/type.ts`: `ReportDisplayConfig` 型と `Result.visualizationConfig` を追加
   - `apps/admin/type.d.ts`: 同上

#### 検証
- TypeScript ビルド: 成功 ✅
- API Python lint: 成功 ✅
- report-schema lint: 成功 ✅

#### 残タスク（Phase 5 に移行）
- Admin API の visualization config CRUD エンドポイント
- draft/publish フロー
- invalidate_report_cache との統合
- report_launcher.py の workflow id 出力

## 2026-01-20

### YouTube入力プラグイン実装

#### 背景
ユーザーの要望: YouTube入力コネクタをプラグインとして実装したい
- YouTube API Keyなどの追加設定を要求する
- 使わない人にはデフォルトでONにしたくない
- プラグインが必要とする設定をコードで管理
- 設定不良で実行された場合に早期警告

#### 実装内容

1. **プラグインアーキテクチャ基盤** (`apps/api/src/plugins/`)
   - `base.py`: プラグイン基底クラスとマニフェスト
     - `PluginSetting`: 設定項目（環境変数名、型、必須フラグ）
     - `PluginManifest`: プラグインメタデータ（ID、名前、設定リスト、デフォルト有効）
     - `InputPlugin`: 入力プラグイン基底クラス（fetch_data, validate_source, ensure_configured）
     - `PluginConfigError`: 設定エラー例外
   - `registry.py`: プラグインレジストリ
     - `PluginRegistry`: プラグイン登録・検索・一覧
     - `load_builtin_plugins()`: 組み込みプラグインのロード

2. **YouTubeプラグイン** (`apps/api/src/plugins/youtube.py`)
   - マニフェスト設定:
     - `id`: "youtube"
     - `enabled_by_default`: False（APIキー必須のため）
     - `settings`: YOUTUBE_API_KEY（required=True, type=SECRET）
   - 機能:
     - YouTube URL解析（動画、短縮URL、埋め込み、プレイリスト対応）
     - YouTube Data API v3 でコメント取得
     - 出力: comment-id, comment-body, source, url, attribute_* (author, published_at, like_count, video_title)

3. **プラグインAPI** (`apps/api/src/routers/plugins.py`)
   - `GET /admin/plugins`: プラグイン一覧（利用可能状態含む）
   - `GET /admin/plugins/{plugin_id}`: プラグイン詳細
   - `POST /admin/plugins/{plugin_id}/validate-source`: ソースURL検証
   - `POST /admin/plugins/{plugin_id}/import`: データインポート（CSV保存）
   - `POST /admin/plugins/{plugin_id}/preview`: プレビュー取得

4. **TypeScript型定義** (`apps/admin/type.d.ts`)
   - `PluginSetting`: プラグイン設定項目
   - `PluginManifest`: プラグインマニフェスト
   - `PluginImportResult`: インポート結果
   - `PluginPreviewResult`: プレビュー結果

5. **入力タイプ拡張** (`apps/admin/app/create/types/index.ts`)
   - `BuiltinInputType`: "file" | "spreadsheet"
   - `PluginInputType`: `plugin:${string}` 形式
   - `InputType`: 両方を含む Union 型
   - `PluginState`: プラグイン状態管理

6. **オプション依存** (`apps/api/pyproject.toml`)
   - `youtube`: google-api-python-client>=2.150.0
   - `all-plugins`: 全プラグイン依存をまとめたエクストラ

#### テスト追加

1. **プラグイン基盤テスト** (`tests/plugins/test_plugin_registry.py`): 14テスト
   - PluginSetting: 環境変数取得、デフォルト値、型変換
   - PluginManifest: バリデーション、dict変換
   - PluginRegistry: 登録、取得、一覧
   - InputPlugin: 設定検証、ソース検証

2. **YouTubeプラグインテスト** (`tests/plugins/test_youtube.py`): 11テスト
   - URL解析: 標準URL、短縮URL、埋め込み、プレイリスト、無効URL
   - プラグイン: マニフェスト、ソース検証

#### テスト結果
- apps/api: 163 passed, 5 skipped ✅ (新規25テスト)

#### 設計ポイント

1. **早期バリデーション**: `ensure_configured()` で設定不足を即座に検出
2. **デフォルト無効**: `enabled_by_default=False` で明示的な設定を要求
3. **オプション依存**: YouTube API クライアントは `pip install server[youtube]` で追加
4. **API応答にisAvailable**: フロントエンドでプラグインの利用可否を表示可能

#### 次のステップ
- Admin UIでのプラグインタブ表示
- プラグインからのコメント取得フロー統合
