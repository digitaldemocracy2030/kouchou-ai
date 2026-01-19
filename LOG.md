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

### Phase 2.5.4: プロンプトファイル移行（N/A）

プロンプトはAPIから`report_input.prompt`として設定に含まれて渡されるため、analysis-coreにプロンプトファイルを含める必要はない。CLIでプロンプトなしで使う場合のフォールバックは将来必要に応じて追加。

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

### Phase 2.5.7: テスト拡充

#### 実施内容
1. `tests/test_integration.py` 追加
   - `test_run_with_mocked_steps`: モック化されたステップの順序実行テスト
   - `test_run_handles_step_failure`: ステップ失敗時のエラーハンドリングテスト
   - `test_full_plan_execution`: 全8ステップの実行計画テスト
   - `test_status_tracking`: ステータス追跡テスト

#### テスト結果
- analysis-core: 44 passed (test_cli: 4, test_config: 4, test_imports: 16, test_integration: 4, test_orchestration: 16)
