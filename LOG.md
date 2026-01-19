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
