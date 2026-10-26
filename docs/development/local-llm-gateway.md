# ローカルLLMの認証付きゲートウェイ

プロバイダを **ローカル LLM**（`local`）にすると、作成画面の「LocalLLM アドレス」に書いた OpenAI 互換のサーバーへ接続します。Ollama / LM Studio は認証が要らないので、通常は設定不要です。

認証付きの OpenAI 互換ゲートウェイ（組織内の HTTPS ゲートウェイなど）を使う場合は、API の `.env` に次の 2 つを設定します。

```dotenv
LOCAL_LLM_API_KEY=<ゲートウェイの鍵>
LOCAL_LLM_ALLOWED_BASE_URLS=https://gateway.example.com
```

- `LOCAL_LLM_API_KEY`：ゲートウェイへ `Authorization: Bearer` で送る鍵です。未設定のときは `not-needed` を送ります。
- `LOCAL_LLM_ALLOWED_BASE_URLS`：鍵を付けてよい接続先です。カンマ区切りで複数書けます。作成画面のアドレスと同じ形式（`https://gateway.example.com`、`https://gateway.example.com/openai`、`ollama:11434` など）で書けます。

## 鍵を付ける接続先の判定

アドレスと許可リストの各項目を同じ規則で base URL（末尾 `/v1`）に直し、スキーム・ホスト・ポート・パスがすべて一致するときだけ鍵を付けます。大文字小文字、既定のポート（http は 80、https は 443）、末尾の `/` の違いは同じものとして扱います。前方一致ではないので、`https://gateway.example.co` や `https://gateway.example.com.other.test` には鍵を付けません。一致しない接続先には `not-needed` を送るので、ゲートウェイは認証エラーを返します。

この判定は、次のすべてで同じです。

- 作成画面のモデル一覧の自動取得（`GET /admin/models?provider=local`）
- 作成画面・再利用画面の接続確認（`GET /admin/environment/verify`）
- パイプラインのチャット・埋め込みの呼び出し（CLI を含む）

作成画面のモデル一覧は、アドレスを入力している途中でも自動で取得します。許可リストがあれば、入力途中や打ち間違えたアドレスには鍵を送りません。

## 許可リストが空のとき

`LOCAL_LLM_ALLOWED_BASE_URLS` が空なら、これまでどおり、どの接続先にも鍵を付けます。既にゲートウェイを使っている環境が、更新しただけで認証エラーにならないようにするためです。このとき API とパイプラインのログに、許可リストを設定するよう促す警告を 1 回出します。`LOCAL_LLM_API_KEY` を設定したら、許可リストも必ず設定してください。

許可リストに書いた項目がどれも読めない（例: `host:abc` のようにポートが数字でない）場合は、空とは扱わず、どの接続先にも鍵を付けません。読めない項目はログに警告を出して無視します。

変更後は API を再起動します。Docker Compose では `docker compose up -d --force-recreate api` で API コンテナを作り直します。
