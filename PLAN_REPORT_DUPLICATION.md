# レポート複製・再利用機能 計画

## 背景
- Issue #19 では、設定の一部だけ変えて再実行できる「レポート複製・再利用」機能が求められている。
- 現状は config から再実行はできるが、API/UI から複製する導線はない。
- `analysis-core` は出力ディレクトリに `hierarchical_status.json` がある場合、前回実行を参照してステップをスキップできる。

## 目的
- 既存レポートを新しい slug で複製し、元レポートは変更しない。
- タイトルやクラスタ数など小さな変更を許容する。
- 既存成果物を再利用し、LLM/embedding のコストを削減する。
- 管理者のみ利用可能で、元レポートの追跡性を確保する。

## 非目的
- 公開ユーザー向けのセルフサービス複製。
- プロジェクトやテナントを跨ぐ複製。
- 複製時の入力データ差し替え。

## 現状整理 (主要ファイル)
- 設定: `configs/{slug}.json` は `apps/api/src/services/report_launcher.py` で作成。
- 入力: `inputs/{slug}.csv` を extraction / aggregation が参照。
- 出力: `outputs/{slug}/` に各ステップ成果物と `hierarchical_status.json`。
- 管理: `data/report_status.json` を `apps/api/src/services/report_status.py` が管理。
- ストレージ同期: `apps/api/src/services/report_sync.py` が不要成果物を削除。

## 設計概要
1. 管理APIに複製エンドポイントを追加: `POST /admin/reports/{slug}/duplicate`。
2. 新しい slug を作成し、入力/出力をコピーして新 config を書き込む。
3. `hierarchical_status.json` をコピーしてスキップ判定を有効化。
4. `hierarchical_result.json` を削除し、集計は必ず再実行。
5. `analysis-core` を新 config で起動する (ReportInput は不要)。

## API 設計
エンドポイント:
- `POST /admin/reports/{slug}/duplicate`

リクエスト例:
```json
{
  "newSlug": "report-2025-07-dup",
  "overrides": {
    "question": "New question",
    "intro": "New intro",
    "cluster": [5, 10],
    "model": "gpt-4o-mini",
    "provider": "openai"
  },
  "reuse": {
    "enabled": true,
    "forceOverview": false
  }
}
```

レスポンス例:
```json
{
  "success": true,
  "report": {
    "slug": "report-2025-07-dup",
    "status": "processing"
  }
}
```

補足:
- `overrides` は source config に部分適用する。
- `reuse.enabled=false` の場合は成果物コピーなしでフル再実行。
- `reuse.forceOverview=true` の場合は `hierarchical_overview.txt` を削除して再生成。

## 再利用方針 (analysis-core)
`analysis-core` がステップをスキップする条件:
- `hierarchical_status.json` が存在し、`previous` として読み込まれる。
- 新 output dir にステップ成果物が存在する。
- ステップの params が `previous` と一致する。

再利用を成立させるための操作:
- `outputs/{source}/hierarchical_status.json` を `outputs/{new}/` にコピー。
- 必要な成果物を `outputs/{new}/` にコピー。
- `hierarchical_result.json` を削除し、集計を強制実行。
- `forceOverview=true` の場合は `hierarchical_overview.txt` も削除。

再利用の優先度:
- 入力取得が高コストなケース (特に Twitter 取得) では入力データの再利用を最優先する。
- LLM コストが高い `extraction` と `embedding` は次点で最優先に再利用する。

再利用対象として保持すべき成果物:
- `args.csv`, `relations.csv`
- `embeddings.pkl`
- `hierarchical_clusters.csv`
- `hierarchical_initial_labels.csv`
- `hierarchical_merge_labels.csv`
- `hierarchical_overview.txt`
最低限の再利用セット (error からの複製でも使える前提):
- 入力: `inputs/{slug}.csv` (取得コストが高い入力は最優先で再利用)
- 抽出済み: `args.csv`, `relations.csv`
- 埋め込み: `embeddings.pkl`

## ストレージ/クリーンアップ変更
`ReportSyncService.PRESERVED_REPORT_FILES` に追加:
- `embeddings.pkl`
- `hierarchical_initial_labels.csv`
- 既存の `.json`, `args.csv`, `relations.csv`, `hierarchical_clusters.csv`, `hierarchical_merge_labels.csv`, `hierarchical_overview.txt` は維持。

追加ユーティリティ:
- `download_input_file(slug)`
- `download_report_artifacts(slug, patterns)`

## バックエンド処理フロー (複製)
1. 管理者 API キーを検証。
2. source レポートが `ready` または `error` であることを確認 (`processing` は不可)。
3. `newSlug` が未使用かつ安全な形式かを確認。
4. `configs/{source}.json` を読み込み。
5. `overrides` を適用し `name` と `input` を `newSlug` に更新。
6. 入力ファイル存在を確認 (必要ならストレージから取得)。
7. `inputs/{newSlug}.csv` を作成 (source をコピー)。
8. `outputs/{newSlug}/` を作成し、必要成果物をコピー。
9. `hierarchical_status.json` をコピーして再利用を有効化。
10. `hierarchical_result.json` を削除 (必要なら `hierarchical_overview.txt` も削除)。
11. `report_status.json` に `status=processing` で追加。
12. config path を受け取る新 helper で `analysis-core` を起動。

## バックエンド変更点
- 新スキーマ: `ReportDuplicateRequest` / `ReportDuplicateResponse`。
- 新サービス: `duplicate_report()` を `apps/api/src/services/report_launcher.py` か新規ファイルに追加。
- `apps/api/src/services/report_status.py` に `add_new_report_to_status_from_config()` を追加。
- `apps/api/src/routers/admin_report.py` に複製エンドポイントを追加。
- `ReportSyncService` に成果物保持/取得を追加。

## フロントエンド計画 (管理画面)
- `apps/admin/app/_components/ReportCard/ActionMenu/ActionMenu.tsx` に「複製」アクション追加。
- 複製ダイアログ:
  - 新 slug (例: `"{slug}-copy-{YYYYMMDD}"`)
  - タイトル/概要
  - クラスタ数
  - model/provider
  - 再利用トグル、概要再生成トグル
- 送信後は `processing` 表示で既存進捗UIを利用。

## テスト
バックエンド:
- temp dir と fake storage を使った複製フローの単体テスト。
- 新 config の値とファイルコピーの検証。
- `hierarchical_result.json` が削除されて集計が再実行されること。
フロントエンド:
- ダイアログ表示/バリデーション/API 呼び出しテスト。

## ロールアウト
1. `ENABLE_REPORT_DUPLICATION` フラグ配下で API を先行リリース。
2. 安定確認後に管理画面の UI を追加。
3. 管理者向けドキュメント更新。

## 受け入れ条件
- 複製したレポートが管理画面に `processing` で表示される。
- メタデータ変更のみなら集計が再実行され、結果に反映される。
- クラスタ数変更なら抽出は再利用され、クラスタ以降が再実行される。
- プロンプト変更なら依存ステップのみ再実行される。
- 元レポートのファイルが変更されない。
- `error` レポートから複製した場合でも、存在する成果物は再利用される。
- `extraction`/`embedding` 成果物が存在する場合は、それらを再利用してコスト削減できる。

## 未決事項
- 再利用のデフォルト範囲 (全再利用か選択制か)。
- 中間成果物の保持期間と削除ポリシー。
- `error` レポートから複製する際の最小必須成果物 (どこまで揃っていれば再利用するか)。
- `extraction`/`embedding` の成果物が欠けている場合の再実行方針 (段階的に再実行するか)。
- UI で「概要再生成」「抽出再実行」などの詳細オプションを出すか。
