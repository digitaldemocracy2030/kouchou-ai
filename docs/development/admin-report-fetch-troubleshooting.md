# 管理画面で「レポートの取得に失敗しました」と表示される（開発者向け）

ローカル開発環境で管理画面を開いたときのトラブルシュートです。

## 症状
- 管理画面で「レポートの取得に失敗しました」
- コンソールに `ECONNREFUSED` や `/admin/reports 401` が出る

## 原因
- `NEXT_PUBLIC_API_BASEPATH` が実際に起動しているAPIと不一致
- dummy-server が起動していない
- APIキーが不一致（dummy-server は `/admin/reports` などの管理用エンドポイントを `ADMIN_API_KEY`、`/reports` を `PUBLIC_API_KEY` で認証）

## 対処
1) dev サーバをまとめて起動する
   - `make client-dev -j 3`

2) APIの接続先を合わせる
   - dummy-server は `http://localhost:8002` で起動する
   - `make client-dev` は public-viewer / admin の接続先（`NEXT_PUBLIC_API_BASEPATH` / `API_BASEPATH`）を `http://localhost:8002` にして起動するので、`.env` を書き換える必要はない
   - `.env-sample` の既定値 `http://localhost:8000` は Docker の API（`docker compose up api`）向け。public-viewer / admin を個別に起動する場合（`make client-dev-server` / `make client-admin-dev-server` や `pnpm dev`）は、次の値が実際に起動している API と合っているかを確認する
     - `apps/admin/.env` の `NEXT_PUBLIC_API_BASEPATH`（`API_BASEPATH` を書いた場合はサーバー側でそちらが優先される）
     - `apps/public-viewer/.env` の `NEXT_PUBLIC_API_BASEPATH` / `API_BASEPATH`

3) APIキーを揃える
   - `utils/dummy-server/.env` を作成（`utils/dummy-server/.env-sample` をコピー。`make client-setup` が行う）
   - `ADMIN_API_KEY` を `apps/admin/.env` の `NEXT_PUBLIC_ADMIN_API_KEY` と同じ値にする（管理画面の `/admin/reports` など）
   - `PUBLIC_API_KEY` を `apps/public-viewer/.env` の `NEXT_PUBLIC_PUBLIC_API_KEY` と同じ値にする（public-viewer の `/reports`）
   - `.env-sample` の既定値どうしは揃っている（admin は `yyyyyyyyyy`、public-viewer は `xxxxxxxxxx`）

4) `.env` を変えたら再起動
   - `make client-dev -j 3` をやり直す
