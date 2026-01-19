# Client（レポート表示画面）テスト計画

## 概要

このドキュメントは広聴AI Client（port 3000）のE2Eテスト計画を定義します。

**対象URL**: http://localhost:3000
**テストフレームワーク**: Playwright
**テストファイルの場所**: `/test/e2e/tests/client/`

## Client の構造

### ページ構成

1. **トップページ** (`/`)
   - レポート一覧を表示
   - 各レポートをカード形式で表示
   - レポートが0件の場合は空の状態を表示

2. **レポート詳細ページ** (`/[slug]`)
   - 個別レポートの詳細を表示
   - Overview（概要）
   - ClientContainer（インタラクティブな分析）
   - Analysis（分析結果）

### APIエンドポイント

Client は以下のAPIエンドポイントを使用：

1. `/meta/metadata.json` - Meta情報（レポート作成者情報）
2. `/reports` - レポート一覧
3. `/reports/{slug}` - 個別レポート詳細

## テストデータの要件

### 1. Meta情報 (`metadata.json`)

```json
{
  "isDefault": false,
  "reporter": "テスト太郎",
  "message": "これはテスト用のメッセージです",
  "webLink": "https://example.com",
  "privacyLink": "https://example.com/privacy",
  "termsLink": "https://example.com/terms",
  "brandColor": "#2577b1"
}
```

### 2. レポート一覧 (`/reports`)

```json
[
  {
    "slug": "test-report-1",
    "status": "ready",
    "title": "テストレポート1",
    "description": "これは1つ目のテストレポートの説明です",
    "isPubcom": false,
    "visibility": "public",
    "createdAt": "2025-01-15T10:00:00Z"
  },
  {
    "slug": "test-report-2",
    "status": "ready",
    "title": "テストレポート2",
    "description": "これは2つ目のテストレポートの説明です",
    "isPubcom": false,
    "visibility": "public",
    "createdAt": "2025-01-16T11:00:00Z"
  }
]
```

### 3. レポート詳細 (`/reports/{slug}`)

最小限のレポート詳細データ（実際にはもっと複雑）：

```json
{
  "arguments": [
    {
      "arg_id": "arg_1",
      "argument": "これはテスト意見1です",
      "comment_id": 1,
      "x": 0.5,
      "y": 0.5,
      "p": 1.0,
      "cluster_ids": ["cluster_1_1"]
    },
    {
      "arg_id": "arg_2",
      "argument": "これはテスト意見2です",
      "comment_id": 2,
      "x": 0.6,
      "y": 0.4,
      "p": 1.0,
      "cluster_ids": ["cluster_1_1"]
    }
  ],
  "clusters": [
    {
      "level": 1,
      "id": "cluster_1_1",
      "label": "テストクラスタ",
      "takeaway": "テストクラスタの要約です",
      "value": 2,
      "parent": "",
      "density_rank_percentile": 0.8
    }
  ],
  "comments": {
    "1": { "comment": "これはテストコメント1です" },
    "2": { "comment": "これはテストコメント2です" }
  },
  "propertyMap": {},
  "translations": {},
  "overview": "これはテストレポートの概要です。",
  "config": {
    "name": "test-config",
    "question": "テスト質問",
    "input": "test-input",
    "model": "gpt-4",
    "intro": "テストレポートのイントロダクションです",
    "output_dir": "test-report-1",
    "is_embedded_at_local": false,
    "enable_source_link": false,
    "extraction": {
      "workers": 1,
      "limit": 100,
      "properties": [],
      "categories": {},
      "category_batch_size": 10,
      "source_code": "",
      "prompt": "",
      "model": "gpt-4"
    },
    "hierarchical_clustering": {
      "cluster_nums": [5, 20],
      "source_code": ""
    },
    "embedding": {
      "model": "text-embedding-3-small",
      "source_code": ""
    },
    "hierarchical_initial_labelling": {
      "workers": 1,
      "source_code": "",
      "prompt": "",
      "model": "gpt-4"
    },
    "hierarchical_merge_labelling": {
      "workers": 1,
      "source_code": "",
      "prompt": "",
      "model": "gpt-4"
    },
    "hierarchical_overview": {
      "source_code": "",
      "prompt": "",
      "model": "gpt-4"
    },
    "hierarchical_aggregation": {
      "hidden_properties": {},
      "source_code": ""
    },
    "hierarchical_visualization": {
      "replacements": {},
      "source_code": ""
    },
    "plan": [],
    "status": "ready"
  },
  "comment_num": 2,
  "visibility": "public"
}
```

## テストシナリオ

### 1. トップページ（レポート一覧）

#### 1.1 正常系 - レポート一覧の表示

**前提条件:**
- Meta情報とレポート一覧のAPIが正常に応答する

**テスト手順:**
1. http://localhost:3000 にアクセス
2. `waitForLoadState("networkidle")` で読み込み完了を待つ

**期待結果:**
- ページタイトルに「レポート一覧」が表示される
- レポート作成者名が表示される
- 各レポートがカード形式で表示される
- レポートタイトルがクリック可能

#### 1.2 正常系 - 空の状態

**前提条件:**
- レポート一覧APIが空配列`[]`を返す

**テスト手順:**
1. APIをモックして空配列を返す
2. http://localhost:3000 にアクセス

**期待結果:**
- 「レポートが0件です」というメッセージが表示される
- 空の状態の画像が表示される

#### 1.3 異常系 - APIエラー

**前提条件:**
- APIが500エラーを返す

**テスト手順:**
1. APIをモックして500エラーを返す
2. http://localhost:3000 にアクセス

**期待結果:**
- エラーメッセージが表示される

#### 1.4 レポートカードのクリック

**前提条件:**
- レポート一覧が表示されている

**テスト手順:**
1. 最初のレポートカードをクリック
2. URLが `/test-report-1` に変わることを確認

### 2. レポート詳細ページ

#### 2.1 正常系 - レポート詳細の表示

**前提条件:**
- Meta情報とレポート詳細のAPIが正常に応答する

**テスト手順:**
1. http://localhost:3000/test-report-1 にアクセス
2. `waitForLoadState("networkidle")` で読み込み完了を待つ

**期待結果:**
- レポートタイトル（config.question）が表示される
- Overview（overview）が表示される
- 戻るボタンが表示される

#### 2.2 正常系 - 戻るボタン

**前提条件:**
- レポート詳細ページが表示されている

**テスト手順:**
1. 戻るボタンをクリック
2. トップページに戻ることを確認

#### 2.3 異常系 - 存在しないレポート

**前提条件:**
- レポート詳細APIが404を返す

**テスト手順:**
1. http://localhost:3000/non-existent-report にアクセス

**期待結果:**
- 404ページまたはNot Foundメッセージが表示される

### 3. レスポンシブデザイン

#### 3.1 異なる画面サイズでの表示

**テスト対象:**
- デスクトップ（1920x1080）
- タブレット（768x1024）
- モバイル（375x667）

**期待結果:**
- 各画面サイズで適切にレイアウトが調整される
- すべてのコンテンツが表示される

## テスト実装のアプローチ

### APIモックの使用

Playwrightの `page.route()` を使用してAPIレスポンスをモック：

```typescript
test("レポート一覧表示", async ({ page }) => {
  // Meta情報のモック
  await page.route("**/meta/metadata.json", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        isDefault: false,
        reporter: "テスト太郎",
        message: "テストメッセージ",
        brandColor: "#2577b1"
      }),
    });
  });

  // レポート一覧のモック
  await page.route("**/reports", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          slug: "test-report-1",
          status: "ready",
          title: "テストレポート1",
          description: "説明",
          isPubcom: false,
          visibility: "public",
          createdAt: "2025-01-15T10:00:00Z"
        }
      ]),
    });
  });

  await page.goto("http://localhost:3000");
  await page.waitForLoadState("networkidle");

  await expect(page.getByText("レポート一覧")).toBeVisible();
  await expect(page.getByText("テストレポート1")).toBeVisible();
});
```

### フィクスチャの使用

複雑なテストデータは `/test/e2e/fixtures/client/` に配置：

```
test/e2e/fixtures/client/
├── metadata.json           # Meta情報
├── reports.json            # レポート一覧
└── report-detail.json      # レポート詳細
```

## 実装の優先順位

1. **高** - トップページのレポート一覧表示
2. **高** - レポート詳細ページの基本表示
3. **中** - APIエラーハンドリング
4. **中** - 空の状態の表示
5. **低** - レスポンシブデザインテスト

## 注意事項

- Client は Next.js の App Router を使用しているため、必ず `waitForLoadState("networkidle")` を使用
- APIモックは各テストで設定（テスト間の干渉を避けるため）
- レポート詳細の完全なデータ構造は複雑なので、最小限のデータでテスト
- インタラクティブな機能（グラフ、フィルターなど）は別途詳細なテストが必要

## 参考資料

- [Public viewer型定義](/apps/public-viewer/type.ts)
- [Playwright APIモック](https://playwright.dev/docs/mock)
- [Admin画面テスト計画](/test/e2e/TEST_PLAN.md)
