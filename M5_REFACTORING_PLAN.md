# リファクタリング／プラグイン化 計画

## 目的
- アプリ・パッケージ・プラグインを明確に分離した整理された構造にする。
- コアのパイプラインに手を入れずに分析手法をプラグイン拡張できるようにする。
- クライアントの変更を最小化して可視化手法をプラグイン拡張できるようにする。
- 可能な範囲で既存の挙動とデータ契約を維持する。
- 分析処理をPyPIパッケージとして配布し、他のBIツールから再利用できる形にする。
- ブラウザ操作なしで「URL→JSON」まで完結するCLIユースケースを満たす。

## 非目的（今回のリファクタ対象外）
- コア分析アルゴリズムの全面置換。
- UIの大規模な再設計や機能の作り直し。
- インフラ／プロバイダーの変更。

## 重要ユースケース（YouTube URL → JSON）
- 位置づけ: リファクタ後に追加される機能の代表例として設計判断に使う（この計画では実装しない）。
- 前提: 管理画面やブラウザを使わず、CLIで完結。
- 流れ: YouTube URL → コメント取得 → CSV生成 → 分析実行 → JSON出力。
- 配布: PyPIパッケージを `pip`/`uv` でインストールし、CLIで実行。
- 出力: JSONが最終成果。必要なら静的HTMLも生成できると望ましい。

## 現状観察（リポジトリ調査より）
- パイプラインは `server/broadlistening/pipeline` 配下にあり、`server/src/services/report_launcher.py` から呼び出されている。
- `hierarchical_main.py` に手順がハードコードされ、`specs.json`/`hierarchical_specs.json` は計画と検証目的のみに使われている。
- クライアント／管理画面がステップ名・チャート種別を固定で参照している（例: `client/components/report/Chart.tsx`, `client-admin/.../ProgressSteps.tsx`）。
- 結果のconfig型が階層型パイプラインに密結合している。
- 生成結果は `server/broadlistening/pipeline/outputs/{slug}/hierarchical_result.json` に保存され、`hierarchical_aggregation.py` が `config`（plan / prompt / source_codeを含む）を書き込んでいる。
- 進捗は `outputs/{slug}/hierarchical_status.json`、一覧は `server/data/report_status.json`。管理画面は `/admin/reports/{slug}/status/step-json` をポーリングし、固定のステップ名で表示している。
- タイトル/概要更新は `PATCH /admin/reports/{slug}/config` で `configs/{slug}.json` を更新し、`execute_aggregation` を再実行して結果JSONを更新する。
- public clientは `/reports/{slug}` を `report-{slug}` タグで取得し、`invalidate_report_cache` がNext.jsのrevalidate APIを叩く設計。
- `SelectChartButton` は「scatterAll / scatterDensity / treemap」を固定順で表示し、`ClientContainer` は可視化設定をローカルstateで保持している。
- `ClientContainer` の初期値は `selectedChart: "scatterAll"`, `showClusterLabels: true`, `maxDensity: 0.2`, `minValue: 5`, `treemapLevel: "0"` となっている。
- `DisplaySettingDialog` は「適用」操作でのみ密度設定を反映し、切替はセッション内で完結している。
- 入力CSVは `comment-id`, `comment-body`, `source`, `url` を基本とし、追加属性カラムを許容する（`save_input_file` の仕様）。
- `report_launcher` は `--without-html` を指定しており、`hierarchical_visualization` ステップは通常実行されない。
- `specs.json` と `utils.py` の非階層パイプラインが残っており、現行では `hierarchical_*` 系が主経路。

## 目標リポジトリ構成（提案）
- apps/
  - api/                 # server (FastAPI)
  - client/              # レポート閲覧
  - admin/               # 管理画面
  - client-static/       # 静的ビルドサービス
- packages/
  - analysis-core/       # パイプライン実行基盤 + ステップランタイム
  - report-schema/       # JSON schema + TS型 + pydanticモデル
  - ingest/              # 入力コネクタのための拡張ポイント（将来追加）
  - ui-shared/           # 共通UI（重複が明確な場合のみ）
- plugins/
  - analysis/
    - hierarchical-default/
    - ...
  - visualization/
    - treemap/
    - scatter/
    - ...
- tools/
  - scripts/             # ルートのscriptsを移動
- experiments/           # experimental/ を移動
- docs/                  # ドキュメント

## プラグインアーキテクチャ（概要）

### プラグインマニフェスト（分析 + 可視化共通）
- id: 一意なプラグインID（例: analysis.hierarchical.clustering）
- version: semver（互換性チェック用）
- kind: analysis-step | visualization
- entry: エントリポイント
- config_schema: プラグイン設定のJSONスキーマ
- inputs / outputs: 生成・消費するアーティファクトのID
- ui: 表示用メタデータ（ラベル、説明、デフォルト設定など）

### 分析プラグインAPI
- ステップインターフェース: run(ctx, inputs, config) -> outputs
- 依存はファイルパスではなくアーティファクトIDで表現
- 結果configに標準メタデータを記録:
  - plugin id / version / 実行config / model / prompt / source参照
- アーティファクトストア抽象化:
  - まずはローカルFS
  - 将来のオブジェクトストレージに備える

### ワークフロー定義
- ワークフローはプラグインIDの順序と依存で定義
- レポートごとにworkflow id + step config overrideを保持
- 旧configから新workflowへの互換レイヤを用意

### 可視化プラグインAPI（クライアント）
- チャートインターフェース: id, label, component, 対応データ形状, 設定UI
- ローカルプラグイン + API配布の有効化リストでレジストリ構築
- レポートconfigにデフォルトチャートIDを保持可能
- 非エンジニア向け設定:
  - configはJSON/YAMLで保持し、UIはその編集ラッパーとして提供
  - 有効化可能なプラグインは「許可済みリスト」から選択
  - 初期は3種類の可視化のON/OFFのみ（scatterAll / scatterDensity / treemap）
  - デフォルト表示は有効なチャートの先頭（または設定で明示）
  - 運用で必要性が出た項目のみ「簡易編集」として段階的に解放

### 入力コネクタ（CLI向けの拡張ポイント）
- 目的: 外部ソース（YouTubeなど）から、パイプラインの入力CSVを生成できる設計にする（実装は別フェーズ）。
- 出力CSVの基本列: `comment-id`, `comment-body`, `source`, `url` + 任意属性列（author, likeCount, publishedAt など）。
- 依存はオプション化し、`analysis-core` の本体を軽量に保つ。

## 初期の可視化設定（最小構成）
- 目的: 非エンジニアは「3種類の可視化のON/OFFのみ」で設定できるようにする。
- 設定項目（案）:
  - enabled_charts: ["scatterAll", "scatterDensity", "treemap"] のON/OFF
  - default_chart: enabled_charts内のいずれか（未指定なら先頭）
  - params: { show_cluster_labels?, scatter_density: { max_density?, min_value? } }（管理者の既定値）
- 既定値（パラメータ）:
  - show_cluster_labels: true（`ClientContainer` の初期値と同じ）
  - scatter_density.max_density: 0.2（`ClientContainer` の初期値と同じ）
  - scatter_density.min_value: 5（`ClientContainer` の初期値と同じ）
- 既定値: 既存挙動に合わせ、初期は scatterAll / scatterDensity / treemap の3つをONにする。
- 表示順/初期選択ルール:
  - chart_order があればその順で表示し、default_chart があれば初期選択にする。
  - chart_order が無い場合は enabled_charts の順を表示順に使う。
  - default_chart が無い/無効の場合は enabled_charts 先頭を初期選択にする。
- 将来: 表示順を制御したくなった場合は chart_order を追加する。
- 将来: 可視化プラグインが増えた場合は、enabled_chartsでON/OFFを追加する運用とする。
- 運用: 既定値は初期表示に反映し、ユーザーの一時的な調整（Dialogでの変更）はセッション内のみとする。

## visualization_config のJSON例（案）
```json
{
  "version": "1",
  "enabledCharts": ["scatterAll", "scatterDensity", "treemap"],
  "defaultChart": "scatterAll",
  "chartOrder": ["scatterAll", "scatterDensity", "treemap"],
  "params": {
    "showClusterLabels": true,
    "scatterDensity": {
      "maxDensity": 0.2,
      "minValue": 5
    }
  },
  "updatedAt": "2025-01-01T00:00:00Z",
  "updatedBy": "admin@example"
}
```

## 管理者による可視化パラメータ変更の設計（案）
- 背景: 管理者と一般ユーザーが同じclient画面を使うため、管理者のみが設定変更できる仕組みが必要。
- 前提: public clientは `PUBLIC_API_KEY` のみで `/reports/{slug}` を取得しているため、編集系APIは `ADMIN_API_KEY` 前提で分離が必要。
- 基本方針: 可視化設定はパイプライン設定とは分離してサーバ側に保存し、clientは公開設定（published）のみ読む。管理者はdraftで編集・プレビュー後に公開する。
- 決定事項: 管理者UIは client-admin に集約し、閲覧ドメインと分離する（BASIC認証/IP制限の運用を想定）。
- 設定データモデル（案）:
  - visualization_config: { version, enabled_charts, default_chart, chart_order?, params?, updated_at, updated_by }
  - paramsはプラグイン単位の設定（例: scatterDensityのmax_density / min_value）。
- 保存場所:
  - draft: `settings.CONFIG_DIR/{slug}.visualization.json`（ファイル名固定、`download_all_config_files_from_storage` の対象）
  - published: `settings.REPORT_DIR/{slug}/visualization_config.json`（`PRESERVED_REPORT_FILES` に `.json` が含まれるため同期対象）
  - `/reports/{slug}` で結果JSONにマージして返却（static exportも取り込めるようにする）。
- 編集フロー: client-adminでdraft保存 → publishでpublishedへコピー → `invalidate_report_cache` → public clientに反映。
- API（案）:
  - GET `/admin/reports/{slug}/visualization-config`（draft/publishedを取得）
  - PUT `/admin/reports/{slug}/visualization-config`（draft更新）
  - POST `/admin/reports/{slug}/visualization-config/publish`（published更新 + キャッシュ再検証）
- UI（決定）:
  - 管理者編集UIはclient-adminに配置し、clientと同じ可視化コンポーネントでプレビューする。
  - 編集はdraftに保存し、公開時のみユーザー側に反映する。
  - 初期はON/OFFの切替のみ、必要になったらプラグイン設定UIを追加する。
  - client-adminの既存Server Action（`updateReportConfig`）と同様の流れで可視化設定の保存・公開を行う。
  - もし将来clientに編集モードを入れる場合は、ADMIN_API_KEYをブラウザに露出させないためサーバ側プロキシ（NextのRoute/Server Action）を用意する。
  - 「表示設定」ダイアログの既定値リセットは、publishedの `visualization_config` を再読み込みして反映する。
- 権限・安全性:
  - admin APIキー必須。公開APIからの編集は不可。
  - 設定はプラグインのschemaでバリデーション、未知のプラグインIDは拒否。
- キャッシュ／配信:
  - publish時に `invalidate_report_cache` を呼び出してNext.js再検証。
  - 既存の `execute_aggregation` は不要（可視化設定の更新でパイプライン再実行はしない）。
  - 静的エクスポート（`NEXT_PUBLIC_OUTPUT_MODE=export`）は再ビルドが必要になる前提で整理する。
- 互換性:
  - 設定が無い場合は既定値（3つON）で描画し、回帰を回避。
  - 現状client UIで調整可能なパラメータ（密度閾値、ラベル表示など）は、管理者がデフォルト値を設定できるようにする。

## 実装影響箇所（コードベースの当たり）
- `server/src/routers/report.py`: `/reports/{slug}` で `visualization_config.json` を読み込み、レスポンスへマージ。
- `server/src/routers/admin_report.py`: 可視化設定のGET/PUT/PUBLISHエンドポイントを追加。
- `server/src/services/report_sync.py`: `.json`は保持対象なのでpublished configはそのまま同期可能。draftはconfig側に置き、既存のconfig同期に乗せる。
- `server/src/repositories/config_repository.py`: `ReportConfig` とは別の `VisualizationConfigRepository` を新設して分離。
- `client/components/report/ClientContainer.tsx`: `visualization_config` を初期stateに反映（selectedChart / showClusterLabels / maxDensity / minValue）。
- `client/components/charts/SelectChartButton.tsx`: `enabled_charts` から動的にタブ生成。要素数の増減に対応するレイアウト調整。
- `client/components/report/DisplaySettingDialog.tsx`: 管理者既定値に戻すUI（リセット）を追加し、published値を再適用できるようにする。
- `client/type.ts`: `Result` に `visualization_config` を追加。
- `client-admin/app/_components/ReportCard/ReportEditDialog/*`: 既存のServer Actionパターンを踏襲して可視化設定用のUI/Actionを追加。
- `client-admin/type.d.ts`: `visualization_config` を追加。

## 進捗状況

| Phase | 状態 | 完了日 |
|-------|------|--------|
| Phase 0 | ✅ 完了 | 2026-01-19 |
| Phase 1 | ✅ 完了 | 2026-01-19 |
| Phase 2 | ✅ 完了 | 2026-01-19 |
| Phase 2.5 | ✅ 完了 | 2026-01-19 |
| Phase 3 | 📋 未着手 | - |

### Phase 2.5 詳細実績
- 2.5.1: initialization関数の移行 ✅
- 2.5.2: PipelineOrchestrator完成 ✅
- 2.5.3: CLI実装完成 ✅
- 2.5.4: デフォルトプロンプト移行 ✅
- 2.5.5: apps/api統合 ✅
- 2.5.7: テスト拡充 ✅
- 2.5.8: リリース準備 ✅

### テスト結果
- analysis-core: 56 passed ✅
- apps/api: 135 passed, 5 skipped ✅
- Dockerビルド: 成功 ✅

---

## 移行計画（フェーズ別）

### Phase 0: 現状把握・棚卸し
- エントリポイントとビルド経路の整理（docker compose / Makefile / scripts）。
- 既存レポート結果JSONの契約を確定。
- client/admin間の重複UIの洗い出し。

### Phase 1: リポジトリ構成の整理
- `apps/` と `packages/` を導入。
- 移動:
  - `server` -> `apps/api`
  - `client` -> `apps/client`
  - `client-admin` -> `apps/admin`
  - `client-static-build` -> `apps/client-static`
- docker compose / Makefile / scripts / docs を新パスに更新。
- 必要に応じてワークスペース（pnpm or npm）導入。

### Phase 2: Analysis Core 抽出
- `packages/analysis-core` を作成:
  - pipeline runner（init / plan / run_step / status）
  - step interface / artifact store
  - `utils.py` / `hierarchical_utils.py` の統合置換
- CLIエントリ（python -m analysis_core.run ...）を提供。
- runner / plan の基本テストを追加。

### Phase 2.5: PyPIパッケージ化
- `analysis-core` をPyPI配布可能な形に整理（pyproject.toml / versioning / release手順）。
- CLIとライブラリAPIの両方を提供（BIツールから呼べる安定API）。
- 出力形式はJSONを正式仕様として固定（他形式は将来拡張で検討）。
- 依存ライブラリを軽量化し、オプション依存を切り分け。
- 配布戦略は段階式: まずanalysis-coreのみでAPI/JSON仕様を固定し、その後「公式プラグイン同梱版」を追加する。

### Phase 2.6: なし（機能追加は別フェーズ）
- CLI/入力コネクタ/HTML出力は新機能のため、リファクタリング計画には含めない。
- 本計画では「拡張ポイントを用意すること」に留め、具体実装は別ロードマップで扱う。

### Phase 3: 分析プラグイン化
- プラグイン探索機構:
  - `plugins/analysis` のローカルプラグイン
  - 追加パスはconfig or envで指定
- 既存ステップをプラグイン化:
  - extraction / embedding / hierarchical_clustering / hierarchical_* 全般
  - prompts をプラグイン配下へ移動
- ハードコードされた手順をworkflow定義へ置換。
- 互換レイヤ:
  - 旧config受理 → runtimeでworkflow configへ変換
- `Analysis` 画面が参照する `result.config.plan` と `result.config.<step>.source_code/prompt/model` は当面互換維持し、UI更新は後続フェーズに回す。

### Phase 4: API & Schema 更新
- `packages/report-schema` を作成:
  - レポート結果/設定のJSON schema
  - client/admin向けTS型
  - server向けpydanticモデル
- `report_launcher.py` を更新し workflow id + step config を出力。
- APIでプラグイン・ワークフローメタデータを返せるようにする。
- `/reports/{slug}` のレスポンスに `visualization_config` をマージ（`visualization_config.json` が存在する場合）。
- `client/type.ts` / `client-admin/type.d.ts` に `visualization_config` を追加。
- APIレスポンスの命名はcamelCase（`SchemaBaseModel` のalias）で統一し、ファイル保存時のsnake_caseとの差はschemaで吸収する。

### Phase 5: 管理画面（Admin）更新
- ワークフロー選択UIとステップ別設定UIを追加（schema駆動）。
- 可視化プラグインの選択UIを追加（非エンジニア向けにプリセット優先）。
- 進行ステップ表示をAPI由来のステップ一覧に変更。
- 入力検証を plugin schema で統一（client / server）。
- `visualization_config` のCRUD用API/Repositoryを追加し、公開時のみ `invalidate_report_cache` を実行。

### Phase 6: クライアント可視化プラグイン化
- visualizationプラグインレジストリを導入。
- `Chart.tsx` をプラグイン動的レンダリングに変更。
- レポートconfigにデフォルトチャートIDを追加。
- 既存 treemap / scatter をデフォルトプラグイン化。
- `ClientContainer` の初期stateを `visualization_config` から設定（selectedChart / showClusterLabels / density params）。
- `SelectChartButton` を `enabled_charts` + `chart_order` から動的生成し、無効化/非表示を制御。

### Phase 7: ドキュメント＆例
- 分析・可視化のプラグイン作成ガイド。
- サンプルプラグイン／テンプレート追加。
- README / 開発ドキュメント更新。

### Phase 8: 清掃・非推奨化
- 旧エントリ（`hierarchical_main.py`, 旧specs）を非推奨化。
- 必要なら旧config移行スクリプトを提供。
- 不要ディレクトリの削除／アーカイブ。

## 開発分担と手順（Codex/Claude Code vs Devin.ai）

### 分担の原則
- ローカル（Codex/Claude Code）: 変更範囲が広い／依存が絡む／実行検証が必要／秘密情報に触れる可能性がある作業を担当。
- Devin.ai: 仕様が固定され、変更範囲が限定される作業（新規モジュールの下地、UIの一部、ドキュメント、ユニットテスト追加など）を担当。
- Devin.aiの成果は必ずローカルでレビューし、統合と検証はローカルで行う。

### フェーズ別の担当割り（提案）
| Phase | ローカル（Codex/Claude Code） | Devin.ai | 補足 |
| --- | --- | --- | --- |
| Phase 0 | 現状調査、設計方針の確定 | なし | 仕様ブレを避けるためローカル集中 |
| Phase 1 | リポジトリ移動、Docker/Makefile更新 | なし | 影響範囲が広く統合リスクが高い |
| Phase 2 | analysis-core抽出と統合 | analysis-coreの雛形作成、単体テスト雛形 | 仕様確定後に限定タスクとして切り出し |
| Phase 2.5 | PyPIパッケージ化の統合 | 配布ドキュメント草案 | リリース手順はローカルで確定 |
| Phase 3 | プラグイン化の統合・互換維持 | 既存ステップの個別プラグイン化（単位ごと） | プラグイン仕様確定後に細分化 |
| Phase 4 | API/Schema統合、実装反映 | TS型/JSON schemaの更新 | スキーマ確定後の機械的変更を委譲 |
| Phase 5 | API実装、publish/revalidate統合 | client-admin UIの一部実装 | API契約を固めた上でUI部分を切り出し |
| Phase 6 | client統合、可視化レジストリ実装 | 既存チャートのアダプタ実装 | UI仕様が安定してから委譲 |
| Phase 7 | ドキュメント統合 | ドキュメント作成 | Devinに一括委譲しやすい |
| Phase 8 | cleanup/移行判定 | なし | 破壊的変更はローカルで実施 |

### Devin.ai への切り出し手順（推奨）
1. ローカルで仕様確定（API契約・型・入出力・受け入れ基準）。
2. Devinに渡す「短いタスク仕様」を作成（目的／範囲／変更ファイル／完了条件）。
3. Devinの成果をローカルでレビューし、統合前にテストを実行。
4. 失敗時はローカルで修正し、再委譲は最小限にする。

## 検証方針（各フェーズで既存機能を壊さない）
- 共通:
  - 重要な機能パス（レポート作成→閲覧→管理更新）をスモークテストで毎回確認する。
  - 可能なら「ゴールデン出力（hierarchical_result.json）」の差分比較を行い、意図しない変化を検出する。
- Phase 1（構成移動）:
  - docker compose の起動確認、`/reports` と `/admin/reports` の疎通確認。
  - 既存の `make` タスクや `test:e2e` が動くことを確認。
- Phase 2（analysis-core抽出）:
  - 既存の入力からパイプラインを実行し、出力JSONが同一（または許容差）であることを確認。
  - `server/tests` のpytestを通す（Makefileの `test/api` 相当）。
- Phase 2.5（PyPI化）:
  - `analysis_core` をライブラリとしてimportできること、CLIが実行できることを確認。
  - JSON出力のスキーマ検証を追加・実行。
- Phase 2.6（新機能）:
  - リファクタ検証には含めない（別ロードマップで定義する）。
- Phase 3（分析プラグイン化）:
  - 同一configでプラグイン版/旧版の出力を比較。
  - `Analysis` 画面が plan/source_code/prompt を表示できることを確認。
- Phase 4（API/Schema）:
  - `/reports/{slug}` のレスポンスに `visualization_config` が正しくマージされることを確認。
  - client/adminの型整合（TypeScriptビルド）を確認。
- Phase 5（管理画面）:
  - adminで可視化設定を保存・公開し、public clientに反映されることを確認。
  - `invalidate_report_cache` が動作することを確認。
- Phase 6（可視化プラグイン化）:
  - `enabled_charts` で表示タブが切り替わることを確認。
  - 既定パラメータが初期表示に反映され、ユーザー調整はセッション内のみであることを確認。
- Phase 7/8（ドキュメント/清掃）:
  - ドキュメント記載と実装が一致しているか確認。
  - 旧エントリ削除は、全テスト通過後に実施。

## リスクと対策
- 既存レポート互換性の崩れ:
  - 旧config/旧resultを読む互換リーダーを保持。
- プラグインの安全性:
  - allowlist + ローカルパス限定をデフォルトに。
- ビルド複雑化:
  - workspacesは段階的導入、移動ごとに検証。

## 受け入れ基準
- `plugins/analysis` に新規プラグインを追加し、workflow configで参照するだけで新ステップが有効化できる。
- `plugins/visualization` に新規チャートを追加し、コアのclientコードを触らずに有効化できる。
- 既存のレポート生成と閲覧がエンドツーエンドで動作する。
- 入力コネクタ／CLI機能を追加できる拡張ポイントが設計として用意されている（実装は別計画）。

## 付録: YouTube入力コネクタ（新機能）開発計画
- 位置づけ: リファクタ完了後の機能追加。ここでは参考計画として記載。
- 目的: YouTube URL からコメントを取得し、CSV→JSONまでをCLIで完結させる。
- CLI案:
  - `kouchou-ai ingest youtube --url <URL> --out input.csv`
  - `kouchou-ai run --input input.csv --output result.json --question ... --intro ...`
  - `kouchou-ai analyze youtube --url <URL> --out result.json`（一括）
  - `kouchou-ai export-html --result result.json --out ./report`（任意）
- 入出力:
  - 入力: YouTube動画URL（将来はプレイリスト/チャンネル対応を検討）。
  - 出力CSV: `comment-id`, `comment-body`, `source`, `url` + 任意属性列（author, likeCount, publishedAt など）。
  - 出力JSON: `analysis-core` の標準結果JSON。
- 依存/認証:
  - YouTube APIクライアントはオプション依存として提供（例: `kouchou-ai[youtube]`）。
  - APIキー/クォータの扱い、コメント無効・取得制限のエラーハンドリングを用意。
- テスト:
  - API呼び出しはスタブ/フィクスチャで検証し、CSV生成の仕様を固定する。
  - 取得件数の上限やページング挙動をユニットで確認する。
