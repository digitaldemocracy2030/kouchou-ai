# E2E テスト

このディレクトリには管理画面のE2Eテストが含まれています。

## 前提条件

- Node.js 18以上
- Playwright のインストール

## セットアップ

```bash
# Playwrightをインストール
npm init playwright@latest

# 依存関係をインストール
npm install
```

## テストの実行

```bash
# すべてのテストを実行
npx playwright test

# 特定のテストを実行
npx playwright test tests/admin/create-report.spec.ts

# UIモードでテストを実行
npx playwright test --ui
```

## テスト内容

- `tests/admin/create-report.spec.ts`: レポート作成機能のテスト
