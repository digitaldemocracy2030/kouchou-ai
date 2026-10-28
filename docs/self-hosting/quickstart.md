# クイックスタート

このガイドでは、広聴AIを最短で使い始めるための手順を説明します。

## 前提条件

- **Docker**: Docker Desktop または Docker Engine がインストールされていること
- **OpenAI API キー**: レポート生成に必要です（ローカルLLM使用時は不要）。ChatGPT Plus とは別に API の課金設定（クレジット購入）が必要です。[APIの課金と429エラー](api-billing-and-rate-limits.md)を参照してください

!!! tip "OS別の詳細なセットアップ"
    詳細なセットアップ手順は各OS向けガイドをご覧ください：

    - [Windows セットアップ](windows-setup.md)
    - [Mac セットアップ](mac-setup.md)
    - [Linux セットアップ](linux-setup.md)

## 開発者向けクイックスタート

### 1. リポジトリをクローン

    git clone https://github.com/digitaldemocracy2030/kouchou-ai.git
    cd kouchou-ai

### 2. 環境設定

    cp .env.example .env

`.env` ファイルを編集して、以下の項目を設定します：

    # 必須: OpenAI API キー
    OPENAI_API_KEY=sk-your-api-key-here
    
    # オプション: 環境設定
    ENVIRONMENT=development

### 3. アプリケーションの起動

    docker compose up

初回起動時は Docker イメージのビルドに数分かかります。

### 4. アクセス

起動完了後、ブラウザで以下の URL にアクセスできます：

| サービス | URL | 説明 |
|---------|-----|------|
| レポート一覧 | http://localhost:3000 | 生成されたレポートを閲覧 |
| 管理画面 | http://localhost:4000 | レポートの作成・管理 |
| API | http://localhost:8000 | バックエンド API |

!!! note "他の端末からのアクセス"
    既定では、各ポートはこの PC（127.0.0.1）からだけ接続できます。同じ LAN の他の端末から接続させたい場合は、`.env` の `HOST_BIND_ADDRESS` を `0.0.0.0` などに変更してください。その場合は、管理画面に `BASIC_AUTH_USERNAME` / `BASIC_AUTH_PASSWORD` を設定し、`ADMIN_API_KEY` と `NEXT_PUBLIC_ADMIN_API_KEY` を推測されにくい同じ値に変更してください。

    他の端末のブラウザは `localhost` ではこの PC に届かないので、`NEXT_PUBLIC_API_BASEPATH` と `NEXT_PUBLIC_CLIENT_BASEPATH` も、他の端末から届くこの PC のアドレス（例: `http://192.168.0.10:8000` と `http://192.168.0.10:3000`）に変えてください。`NEXT_PUBLIC_` で始まる値はビルド時に埋め込まれるので、変えたら `docker compose up -d --build` で作り直します。

    Ollama（`--profile ollama`）のポートは認証がないため、`HOST_BIND_ADDRESS` を変えてもこの PC からだけ接続できるままです（`OLLAMA_HOST_BIND_ADDRESS` で別に設定します）。アプリはコンテナ間通信で Ollama に接続するので、通常は変える必要はありません。

    以前のバージョンでは各ポートがすべてのネットワークに公開されていました。他の端末やサーバー外から直接接続していた場合は、上記のとおり `HOST_BIND_ADDRESS` を設定してください。なお `PUBLIC_API_KEY`（公開ビューア用の API キー）はブラウザに配信される値なので秘密になりません。外部に公開する場合は、`ENVIRONMENT=production` に変更することも検討してください。

## ローカル開発（Dockerを使わずに起動）

Dockerを使わずに `apps/api` と `apps/admin` を個別に起動する場合は、以下を実行します。

### 1. API 側の環境変数

リポジトリ直下で `apps/api/.env` を作成し、最低限以下を設定します（リポジトリ直下の `.env.example` を `apps/api/.env` にコピーして編集しても構いません）：

    ADMIN_API_KEY=admin
    PUBLIC_API_KEY=public
    OPENAI_API_KEY=sk-your-api-key-here
    LOG_FILE=error.log

`LOG_FILE` は API を起動するディレクトリ（`apps/api`）からの相対パスです。上の例では `apps/api/error.log` に出力されます。

### 2. API 依存のセットアップと起動

    cd apps/api
    rye sync
    rye run python -m ensurepip --upgrade
    rye run python -m pip install -e ../../packages/analysis-core
    make run

!!! note "analysis-core について"
    analysis-core が未インストールだと `No module named analysis_core` で失敗します。上記の editable install を必ず実行してください。

### 3. 管理画面（admin）の環境変数

API は起動したままにして、別のターミナルを開き、リポジトリ直下で以下を実行します。

    cp apps/admin/.env-sample apps/admin/.env

`apps/admin/.env` を以下のように設定します。`NEXT_PUBLIC_ADMIN_API_KEY` は、API 側の `ADMIN_API_KEY` と同じ値にしてください（`.env-sample` の初期値 `yyyyyyyyyy` のままでは管理画面から API を呼べません）：

    NEXT_PUBLIC_CLIENT_BASEPATH=http://localhost:3000
    NEXT_PUBLIC_API_BASEPATH=http://localhost:8000
    NEXT_PUBLIC_ADMIN_API_KEY=admin

### 4. 管理画面の起動

    cd apps/admin
    pnpm dev

!!! tip "APIのエラー確認"
    `LOG_FILE` を設定している場合は `apps/api/error.log` にエラーが出力されます。

## 基本的な使い方

### レポートの作成

1. http://localhost:4000 にアクセス
2. 「新規レポート作成」をクリック
3. CSV ファイルをアップロード（コメントデータ）
4. 設定を調整して「レポート生成」を実行
5. 生成完了後、http://localhost:3000 でレポートを確認

### CSV ファイルの形式

    comment-body
    これは最初のコメントです。
    これは2番目のコメントです。
    意見が含まれるテキストをここに入力します。

!!! info "おすすめのクラスタ数設定"
    コメント数の立方根（∛n）を四捨五入した値を一層目、その二乗を二層目の目安にすることをお勧めします。ただし、推奨値の計算では一層目は 2〜10 の範囲に収められます。CSV ファイルを読み込むと、この値が初期値として入ります：

    | コメント数 | 一層目 | 二層目 |
    |-----------|-------|--------|
    | 125件 | 5 | 25 |
    | 400件 | 7 | 49 |
    | 1000件 | 10 | 100 |
    | 8000件 | 10 | 100 |

## 次のステップ

- [使い方の詳細](../user-guide/how-to-use.md)
- [CLI からの実行](../user-guide/cli-quickstart.md)
- [Azure へのデプロイ](../deployment/azure.md)
- [静的ホスティング向け CSP 設定](../deployment/static-hosting-csp.md)

## トラブルシューティング

### Docker が起動しない

Docker Desktop が起動しているか確認してください。

    docker --version
    docker compose version

### API キーのエラー

`.env` ファイルの `OPENAI_API_KEY` が正しく設定されているか確認してください。

### 管理画面のレポートリンクが `undefined` になる

管理画面のレポートリンクが `http://localhost:4000/undefined/...` になる場合は、
`apps/admin/.env` に `NEXT_PUBLIC_CLIENT_BASEPATH` が未設定です。

    NEXT_PUBLIC_CLIENT_BASEPATH=http://localhost:3000

設定後に `pnpm dev` を再起動してください。

### ポートが使用中

他のアプリケーションが同じポートを使用している場合は、該当するアプリケーションを停止してください。

レポート閲覧画面（3000）・管理画面（4000）・API（8000）のポートは `.env` では変えられません（`.env` で変えられるのは Ollama の `OLLAMA_HOST_PORT` だけです）。変える必要がある場合は、Docker で起動しているなら `compose.yaml` の `ports` のホスト側（`"${HOST_BIND_ADDRESS:-127.0.0.1}:8000:8000"` の 2 つ目の `8000`）を、Docker を使わずに起動しているなら `apps/api/Makefile` の `--port 8000` や `apps/admin/package.json` の `-p 4000` を編集します。その場合は、`NEXT_PUBLIC_API_BASEPATH` や `NEXT_PUBLIC_CLIENT_BASEPATH` など、そのポートを指す URL の設定も合わせて変えてください。
