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
