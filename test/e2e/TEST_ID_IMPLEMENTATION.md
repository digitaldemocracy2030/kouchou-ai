# テストID実装ガイド

このドキュメントでは、E2Eテストで使用するテストID（data-testid属性）の実装方法について説明します。

## 概要

テストIDを使用することで、以下のメリットがあります：

- UIの変更に強い：テキストやCSSが変更されてもテストが壊れにくい
- 明示的：テスト対象の要素が明確に識別される
- メンテナンス性：テストコードが読みやすく、保守しやすい

テストを実装する際、テスト対象の側にTest IDを付与して壊れにくいテストにすることが推奨されます。

## 実装方法

### 1. コンポーネントにdata-testid属性を追加

```tsx
// 例: BasicInfoSection.tsx
<FormControl>
  <FormLabel>タイトル</FormLabel>
  <Input 
    data-testid="title-field"
    value={title} 
    onChange={(e) => setTitle(e.target.value)} 
  />
</FormControl>
```

### 2. 推奨するテストID命名規則

- ページタイトル: `{page-name}-title`
- フォームフィールド: `{field-name}-field`
- ボタン: `{action}-button`
- タブ: `{tab-name}-tab`
- ファイルアップロード: `file-upload`

### 3. 管理画面で実装が必要なテストID

以下のテストIDを実装することで、E2Eテストが正常に動作します：

| 要素 | テストID |
|------|----------|
| レポート作成ページのタイトル | `create-report-title` |
| タイトル入力フィールド | `title-field` |
| 調査概要入力フィールド | `intro-field` |
| ID入力フィールド | `id-field` |
| CSVタブ | `csv-tab` |
| ファイルアップロード | `file-upload` |
| 送信ボタン | `submit-button` |

## テストコードでの使用方法

```typescript
// Page Objectでの使用例
this.titleField = page.getByTestId('title-field');

// テストでの使用例
await expect(page.getByTestId('create-report-title')).toBeVisible();
```
