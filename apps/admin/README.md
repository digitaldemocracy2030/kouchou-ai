# @kouchou-ai/admin

デジタル民主主義2030 ブロードリスニングの管理者用フロントエンドです

## Usage

```
pnpm install
pnpm run build
pnpm start
```

## Environment variables

- `NEXT_PUBLIC_CLIENT_BASEPATH`
    - public-viewer が動作するエンドポイント
- `NEXT_PUBLIC_API_BASEPATH`
    - api が動作するエンドポイント
- `NEXT_PUBLIC_ADMIN_API_KEY`
    - api の管理向けAPIを利用するためのAPIキー
- `ADMIN_API_KEY`
    - サーバー側（再利用設定の取得 `/api/admin/reports/[slug]/config` と、レポート複製の Server Action）が api の管理向けAPIを呼ぶときのAPIキー。`NEXT_PUBLIC_ADMIN_API_KEY` と同じ値を設定する
    - ビルド時ではなく実行時に読まれるので、admin を動かす環境（コンテナ等）の環境変数として渡す
- `BASIC_AUTH_USERNAME`
    - basic 認証のユーザー名 (空欄の場合は認証スキップ)
- `BASIC_AUTH_PASSWORD`
    - basic 認証のパスワード (空欄の場合は認証スキップ)
