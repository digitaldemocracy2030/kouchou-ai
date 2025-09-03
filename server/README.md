# kouchou-ai-server
kouchou-aiのAPIサーバーです。
レポートの作成、取得などを行うことができます。

## 開発環境

* rye
* python 3.12
* OpenAI API Key
* Gemini API Key ([取得方法](https://ai.google.dev/gemini-api/docs/api-key))


## セットアップ（開発環境）
プロジェクトのルートディレクトリ（kouchou-ai/）にまだ.envがない場合は、kouchou-ai/で以下のコマンドを実行し、.envファイル内の環境変数を記載してください。
すでに.envがある場合は、最新のenv.exampleと比較して、欠けている内容があれば追加してください。
```bash
cp .env.example .env
```
ユーザーが設定できるLLMモデルの環境変数設定は以下の通りです。（最低どっちか片方あれば、動作確認できます）
* OPENAI_API_KEY
  * OpenAIのAPIキー。レポート作成時に利用。
* OPENROUTER_API_KEY
  * OpenRouterのAPIキー。OpenRouter経由でOpenAIやGeminiのモデルを使用する場合に必要。
  * [OpenRouter](https://openrouter.ai/)でアカウントを作成し、APIキーを取得してください。
* GEMINI_API_KEY
  * GoogleAIStudioのAPIキー。レポート作成時に利用。

※ APIキーは他人と共有しないでください。GithubやSlackにもアップロードしないよう注意してください。  
※ このキーを設定しなくてもサーバーは起動しますが、/admin/reportsなど一部のエンドポイントでエラーになります。  
※ APIキーを設定してレポート作成などを行うと、OpenAI APIまたはOpenRouter APIの使用料金が発生します。料金は各サービスの公式ドキュメントを参照してください。  
※ OpenAI APIまたはOpenRouter APIを使用しない機能は無料で利用できます（通常のインターネット利用の通信料等は除く）。

## 起動
プロジェクトのルートディレクトリ（kouchou-ai/）で以下のコマンドを実行してください。
```bash
docker compose up api
```

起動後、 `http://localhost:8000/docs` でSwagger UIが立ち上がるので、
そちらでAPIの動作を確認できます。

## 認証が必要なエンドポイントについて

一部のエンドポイントでは、**APIキーによる認証**が必要です。  
APIキーには **管理者用** と **公開用** の2種類があります。

### 1. 管理者用APIキー
`/admin/reports` などの管理者向けエンドポイントは、**管理者用APIキー** が必要です。  
Swagger UI 右上の **Authorize** ボタンをクリックし、`.env` ファイルで設定した `ADMIN_API_KEY` を入力してください。

このキーを入力すると、レポート作成やコメントデータの取得など、管理者向けの操作が可能になります。

### 2. 公開用APIキー
`/reports` や `/reports/{slug}` などのエンドポイントは、**公開用APIキー** が必要です。  
同じく Swagger UI の **Authorize** ボタンから、`.env` ファイルで設定した `PUBLIC_API_KEY` を入力してください。

このキーを入力することで、作成済みのレポート一覧や特定のレポートデータを取得できます。

### 注意事項
- APIキーが未入力、または無効な場合は **401 Unauthorized** エラーになります。

## 開発用Tips
- **ホットリロード対応**  
  `server` フォルダ内のコードを編集して保存すると、自動的にサーバーが再起動します。  
  手動で再起動する必要はありません。

- **サーバーの終了**  
  `docker compose up api` を実行したターミナルで **Ctrl + C** を押すと停止できます。

- **envファイルを編集した場合**  
  .env の内容を変更した場合は、サーバーを終了した後に以下のコマンドでサーバーを再起動してください。
```bash
docker compose down
docker compose up api
```

## OpenRouterの使用方法

OpenRouterを使用する場合は、以下の手順で設定を行ってください：

1. [OpenRouter](https://openrouter.ai/)でアカウントを作成
2. APIキーを取得し、`.env`ファイルの`OPENROUTER_API_KEY`に設定
3. 使用したいモデルを指定（例：`openai/gpt-4`、`google/gemini-pro`など）

OpenRouterを使用する利点：
* OpenAIやGoogleのモデルにアクセス可能
* より柔軟なモデル選択が可能
* 料金体系が異なる場合がある

注意事項：
* OpenRouterの料金体系はOpenAIやGoogleとは異なります
* モデルによって利用可能な機能が異なる場合があります
* レスポンス時間はOpenAIやGoogleの直接利用と比べて若干遅くなる可能性があります
