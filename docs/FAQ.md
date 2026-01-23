# 開発者向けFAQ

## 管理画面で「レポートの取得に失敗しました」と表示される

### 症状
- 管理画面で「レポートの取得に失敗しました」
- コンソールに `ECONNREFUSED` や `/admin/reports 401` が出る

### 原因
- `NEXT_PUBLIC_API_BASEPATH` が実際に起動しているAPIと不一致
- dummy-server が起動していない
- APIキーが不一致（dummy-server は `PUBLIC_API_KEY` で `/admin/reports` を認証）

### 対処
1) dev サーバをまとめて起動する  
   - `make client-dev -j 3`

2) APIの接続先を合わせる  
   - `apps/admin/.env` の `NEXT_PUBLIC_API_BASEPATH` / `API_BASEPATH`
   - `apps/public-viewer/.env` の `NEXT_PUBLIC_API_BASEPATH` / `API_BASEPATH`
   - dummy-server の既定は `http://localhost:8000`

3) APIキーを揃える  
   - `utils/dummy-server/.env` を作成（`utils/dummy-server/.env-sample` をコピー）
   - `PUBLIC_API_KEY` を以下と同じ値にする
     - `apps/admin/.env` の `NEXT_PUBLIC_ADMIN_API_KEY`
     - `apps/public-viewer/.env` の `NEXT_PUBLIC_PUBLIC_API_KEY`

4) `.env` を変えたら再起動  
   - `make client-dev -j 3` をやり直す

