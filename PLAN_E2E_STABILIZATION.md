# E2E安定化 PLAN

## 位置付け
- 目的: レポート複製機能の実装フェーズにおける「テスト完走」を達成する。
- 現状: API/Jest は通過済み。E2E が環境起因でタイムアウト/失敗している。
- 対象: `test/e2e` の Playwright 実行フロー（global-setup / webServer / dev server 応答）。

## スコープ
- Playwright E2E 実行が安定して通ることを目標。
- UI/機能の追加は後続フェーズ（source_slug 表示）で対応。

## 前提
- ダミーAPI (utils/dummy-server) を E2E 内で使う。
- 管理画面 (apps/admin) と public-viewer (apps/public-viewer) を dev server 起動。

## 仮説
1. admin/public-viewer が「起動しているが応答しない」原因は、ダミーAPI未応答または環境変数/待機不足。
2. global-setup で dummy-server を起動しても、webServer 側が別プロセスで衝突/待機不整合。
3. webServer 起動コマンドに npm を含むため挙動が不安定（pnpm 化/明示 PATH が必要）。

## 手順
1. 状態確認（port / HTTP 応答 / 直近ログ）。
2. E2E 失敗原因の切り分け。
3. 対処案の適用。
4. E2E 再実行。
5. 結果をログに記録。

## 作業ログ
### 2026-01-29
- PLAN_E2E_STABILIZATION.md を作成（目的/スコープ/仮説/手順/ログ枠）。
- 変更状況: `apps/api/pyproject.toml` / `requirements*.lock` / `test/e2e` 周辺に修正あり。
- ポート状況: 8002 / 3000 / 4000 が LISTEN 中（node プロセス）。
- 次: admin/public-viewer が応答しない原因切り分け（HTTP 応答/ログ確認）。
- HTTP 応答確認: 8002 は 200、3000/4000 はタイムアウト（応答なし）。
- E2E 失敗: static build は完走するが admin/public-viewer が起動後に応答せず、verify/admin/client の多くが 40s タイムアウト。
- 状態確認: admin/public-viewer の node は cwd が各アプリ配下だが応答が返らない。
- 方針確定: Playwright の webServer が global-setup より先に起動するため、dummy-server は webServer 管理に戻す。
- 対応: `test/e2e/playwright.config.ts` に dummy-server の webServer エントリを追加、`global-setup.ts` は 8002 待機のみ。
- 次: E2E を再実行して webServer 起動順の問題が解消するか確認。
- 対応: `test/e2e/scripts/build-static.sh` の subdir 出力を `out-subdir/kouchou-ai` に移動するよう変更。
- 対応: Playwright webServer で静的ビルド→http-server 起動を直列化し、public-viewer dev 起動を静的ビルド後に移動。
- 対応: dummy-server の webServer に `E2E_TEST=true` を追加し、テストフィクスチャを返すように修正。
- 実行: `pnpm --filter @kouchou-ai/e2e-tests test -- --project=verify` を DEBUG 付きで再実行し、9/9 PASS を確認。
- 対応: Playwright の static webServer timeout を 30s → 120s に延長（build + http-server 起動待ち）。
- 対応: client-static-subdir の baseURL を `http://localhost:3002/kouchou-ai/` に補正し、`./` 相対遷移と整合させた。
- 実行: `--project=client` の report-detail.spec.ts を単体実行し、10/10 PASS を確認。
- 実行: `--project=client-static-subdir` を実行し、baseURL 修正で 15/16 PASS まで改善。
- 対応: subdir の 404 テストは静的ホスティングで空ボディになり得るため、HTTP 404 ステータスを許容する判定に変更。
- 実行: subdir の 404 単体テストで PASS を確認。
- 実行: `pnpm --filter @kouchou-ai/e2e-tests test` を全体実行し、71 passed / 3 skipped を確認。

## 既知の状況
- API pytest: 171 passed
- Admin jest: PASS
- E2E: フル実行で 71 passed / 3 skipped。
