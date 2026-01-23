# utils/dummy-server
これはダミーサーバーです  
フロントエンドの開発時にのみ利用してください

## Environment variables
- `PUBLIC_API_KEY`
  - public-viewer からのリクエストを受け付けるためのAPIキー
  - /reports および /reports/:slug へアクセスする際に必要
  - (/ や /meta/** へのアクセスには不要)
- `ADMIN_API_KEY`
  - admin からのリクエストを受け付けるためのAPIキー
  - /admin/reports へアクセスする際に必要

## endpoints
- GET /
  - (ヘルスチェック用)
- GET /meta/metadata.json
  - レポート発行者情報
- GET /meta/reporter.png
  - レポート発行者画像
- GET /meta/icon.png
  - レポートアイコン
- GET /meta/ogp.png
  - OGP画像(1200x630推奨)
- GET /reports
  - レポート一覧
- GET /reports/:slug
  - レポート本体
- GET /admin/reports
  - レポート一覧(公開前含む)
- POST /admin/reports
  - レポート作成

## metadata
- reporter: string
  - レポート作成者名
- message: string
  - レポート作成者からのメッセージ
- webLink?: string
  - レポート作成者URL
- privacyLink?: string
  - プライバシーポリシーURL
- termsLink?: string
  - 利用規約URL
- brandColor?: string
  - ブランドカラー
