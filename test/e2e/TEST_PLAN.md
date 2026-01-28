# 広聴AI 管理画面テストプラン

## 概要

このドキュメントは広聴AI（Kouchou-AI）の管理画面（admin）に対するE2Eテスト計画を定義します。

**対象URL**: http://localhost:4000
**テストフレームワーク**: Playwright
**テストファイルの場所**: `/test/e2e/tests/admin/`

## テスト環境

### 前提条件

- Node.js と pnpm がインストールされていること
- Docker Compose で全サービスが起動していること（`make client-dev -j 3` または `docker compose up`）
- 管理画面が http://localhost:4000 でアクセス可能であること
- APIサーバーが http://localhost:8000 で稼働していること

### テスト実行コマンド

```bash
# E2Eテストディレクトリに移動
cd test/e2e

# すべてのテストを実行
pnpm test

# UIモードでテストを実行
pnpm run test:ui

# デバッグモードでテストを実行
pnpm run test:debug

# 特定のテストファイルのみ実行
pnpm exec playwright test tests/admin/create-report.spec.ts
```

## テストカテゴリ

### 1. 初期表示とナビゲーション

**目的**: 管理画面の基本的な表示と画面遷移を確認

| テストケース | 検証内容 | 優先度 |
|------------|---------|-------|
| トップページの表示 | ページタイトル、ヘッダー、メインコンテンツが正常に表示される | 高 |
| ナビゲーションメニュー | すべてのメニュー項目が表示され、クリック可能である | 高 |
| レポート作成ページへの遷移 | レポート作成ページ（/create）に正常に遷移できる | 高 |

### 2. レポート作成フロー

**目的**: レポート作成の主要機能を検証

| テストケース | 検証内容 | 優先度 |
|------------|---------|-------|
| レポート作成画面の初期表示 | 必要なフォーム要素（レポート名、CSVアップロード、パイプライン設定）が表示される | 高 |
| レポート名の入力と検証 | レポート名の入力、バリデーションエラーの表示 | 高 |
| CSVファイルのアップロード | 正常なCSVファイルのアップロードと確認メッセージ | 高 |
| 不正なファイル形式のエラー | CSV以外のファイルをアップロードした場合の適切なエラー表示 | 中 |
| パイプライン設定の変更 | 各種設定項目の変更と保持の確認 | 中 |
| 必須項目の検証 | 必須項目が未入力の場合の実行防止とエラー表示 | 高 |
| レポート作成の実行 | 完全な入力後の作成実行とローディング表示、完了後の遷移 | 高 |

#### テストデータ

- **正常なCSVファイル**: `test/e2e/fixtures/sample-comments.csv`
- **不正なファイル**: `test/e2e/fixtures/invalid-file.txt`
- **大容量CSVファイル**: `test/e2e/fixtures/large-comments.csv`（パフォーマンステスト用）

### 3. レポート一覧と管理

**目的**: 作成済みレポートの閲覧と管理機能を確認

| テストケース | 検証内容 | 優先度 |
|------------|---------|-------|
| レポート一覧の表示 | 作成済みレポートが一覧表示され、基本情報が確認できる | 高 |
| レポートの検索 | 検索キーワードによるフィルタリング機能 | 中 |
| レポートの詳細表示 | 個別レポートの詳細情報の表示 | 高 |
| レポートの編集 | レポート情報の編集と保存 | 中 |
| レポートの削除 | 削除確認ダイアログと削除実行 | 中 |

### 4. エラーハンドリング

**目的**: 異常系の動作とエラーメッセージを確認

| テストケース | 検証内容 | 優先度 |
|------------|---------|-------|
| APIサーバー停止時のエラー | APIサーバーが停止している場合の適切なエラー表示 | 高 |
| 大容量ファイルアップロード | プログレスインジケーターとタイムアウト処理 | 中 |
| ネットワークエラー時の復旧 | ネットワークエラー発生時のエラー表示と再試行オプション | 中 |

### 5. レスポンシブデザイン

**目的**: 異なる画面サイズでの動作を確認

| デバイス | 画面サイズ | 検証内容 | 優先度 |
|---------|----------|---------|-------|
| デスクトップ | 1920x1080 | レイアウトの適切な表示と機能の動作 | 高 |
| タブレット | 768x1024 | レイアウトの調整と機能の利用可能性 | 中 |
| モバイル | 375x667 | モバイル向けレイアウトと機能の動作 | 中 |

### 6. パフォーマンス

**目的**: 読み込み速度とパフォーマンスを確認

| テストケース | 基準 | 優先度 |
|------------|-----|-------|
| ページ初期読み込み時間 | 3秒以内 | 中 |
| 大量データ表示時のパフォーマンス | スムーズなスクロールとページネーション | 低 |

## テスト実装ガイドライン

### Page Object Model (POM)

複雑な画面操作は Page Object Model を使用して実装します。

```typescript
// test/e2e/pages/AdminCreatePage.ts
export class AdminCreatePage {
  constructor(private page: Page) {}

  async goto() {
    await this.page.goto('http://localhost:4000/create');
  }

  async fillReportName(name: string) {
    await this.page.fill('[data-testid="report-name-input"]', name);
  }

  async uploadCSV(filePath: string) {
    await this.page.setInputFiles('[data-testid="csv-upload"]', filePath);
  }

  async submitForm() {
    await this.page.click('[data-testid="submit-button"]');
  }
}
```

### テストフィクスチャ

テストデータは `/test/e2e/fixtures/` に配置します。

```
test/e2e/fixtures/
├── sample-comments.csv      # 正常なCSVファイル
├── invalid-file.txt         # 不正なファイル形式
├── large-comments.csv       # 大容量テスト用
└── test-config.json         # テスト設定
```

### セレクタの命名規則

- `data-testid` 属性を優先的に使用
- 安定したセレクタを選択（IDや固有のクラス名）
- 動的に変わる可能性のあるテキストやクラスは避ける

```typescript
// 推奨
await page.click('[data-testid="submit-button"]');
await page.click('#report-name-input');

// 非推奨
await page.click('.MuiButton-root.css-xyz123'); // 動的なクラス名
await page.click('text=送信'); // テキストが変わる可能性
```

## CI/CD統合

### GitHub Actions での実行

```yaml
# .github/workflows/e2e-tests.yml
name: E2E Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
      - name: Install dependencies
        run: cd test/e2e && pnpm install
      - name: Install Playwright browsers
        run: cd test/e2e && pnpm exec playwright install --with-deps
      - name: Start services
        run: docker compose up -d
      - name: Wait for services
        run: sleep 30
      - name: Run E2E tests
        run: cd test/e2e && pnpm test
      - uses: actions/upload-artifact@v3
        if: always()
        with:
          name: playwright-report
          path: test/e2e/playwright-report/
```

## トラブルシューティング

### よくある問題

**問題**: テストがタイムアウトする
- **原因**: サービスが起動していない、または遅い
- **解決策**: `docker compose up` でサービスを起動し、準備完了を待つ

**問題**: セレクタが見つからない
- **原因**: UIの変更、読み込み待ちの不足
- **解決策**: `await page.waitForSelector()` を使用して要素の表示を待つ

**問題**: スナップショットが一致しない
- **原因**: 環境の違い、動的なコンテンツ
- **解決策**: `toHaveScreenshot({ maxDiffPixels: 100 })` で許容範囲を設定

## 今後の拡張

- [ ] ビジュアルリグレッションテストの追加
- [ ] アクセシビリティテストの統合
- [ ] パフォーマンス測定の自動化
- [ ] テストカバレッジレポートの生成
- [ ] 並列実行の最適化

## 参考資料

- [Playwright 公式ドキュメント](https://playwright.dev/)
- [広聴AI リポジトリ](https://github.com/your-org/kouchou-ai)
- [CLAUDE.md](../../CLAUDE.md) - プロジェクト全体の開発ガイド
