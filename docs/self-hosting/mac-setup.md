# Mac環境でのユーザーガイド

このドキュメントでは、開発者でない人がMac環境で広聴AI（kouchou-ai）を使うための手順を説明します。
ソフトウェア開発に必要な要素を取り除いて最小限にしたものです。

## 前提条件

- macOS Catalina (10.15) 以降
- インターネット接続
- OpenAI APIキー（[取得方法](https://platform.openai.com/api-keys)）
- Gemini APIキー（[取得方法](https://ai.google.dev/gemini-api/docs/api-key)）

## セットアップ手順

### 1. Docker Desktopのインストール

1. [Docker Desktop for Mac](https://www.docker.com/products/docker-desktop/)をダウンロードしてインストールします。
2. インストール後、Docker Desktopを起動します。
3. メニューバーのDockerアイコンが実行中（緑色）になっていることを確認します。

### 2. 広聴AIのダウンロード

1. [広聴AI安定版リリース](https://github.com/digitaldemocracy2030/kouchou-ai/releases/latest)から最新の安定版をダウンロードします。
2. ダウンロードしたzipファイルを任意の場所に展開します。

### 3. APIキーの準備

1. [OpenAI API](https://platform.openai.com/api-keys)にアクセスし、OpenAI APIキーを取得します（OpenAIモデルを使用する場合）。
2. [Google AI Studio](https://ai.google.dev/gemini-api/docs/api-key)にアクセスし、Gemini APIキーを取得します（Geminiモデルを使用する場合）。
3. 各サービスの利用には課金が発生する場合があります。事前にクレジットをチャージしておくことをお勧めします。

### 4. セットアップの実行

1. ターミナルを開きます。
2. 展開したフォルダに移動します：`cd 展開したフォルダのパス`
3. セットアップスクリプトに実行権限を付与します：`chmod +x setup_mac.sh`
4. 以下のコマンドを実行してセットアップを開始します：`./setup_mac.sh`
5. プロンプトが表示されたら、OpenAI APIキーとGemini APIキーを入力します（どちらか一方でも可）。
6. セットアップが自動的に進行し、Dockerコンテナが起動します。

### 5. アプリケーションへのアクセス

セットアップが完了すると、以下のURLでアプリケーションにアクセスできます：

- レポート閲覧画面: http://localhost:3000
- 管理画面: http://localhost:4000

### 6. アプリケーションのアクセス・運用と再起動の手順

セットアップ後は、次回以降の起動や停止を以下のように行ってください。

#### 通常の起動・停止

- アプリケーションの起動:  
  `./start_mac.sh` を実行します（または Docker デスクトップから操作）

- アプリケーションの停止:  
  `./stop_mac.sh` を実行します（または Docker デスクトップから操作）

#### APIキーを変更したい場合

OpenAI APIキーやGemini APIキーを再設定したい場合は、再度 `./setup_mac.sh` を実行してください。

1. 既存のアプリケーションが起動中の場合は `./stop_mac.sh` で停止してください。  
2. `./setup_mac.sh` を実行し、新しい APIキーを入力します。
3. 自動的に再ビルドと起動が行われます。

> ※ `setup_mac.sh` の再実行では、既存の `.env` ファイルが上書きされます。

## トラブルシューティング

### Docker Desktopが起動していない場合

エラーメッセージ「Docker Desktopが実行されていません」が表示された場合は、Docker Desktopを起動してから再度セットアップスクリプトを実行してください。

### メモリ不足エラーが発生する場合

Docker Desktopの設定からリソース割り当て（メモリ、CPU）を増やしてください。推奨設定：

- メモリ: 4GB以上
- CPU: 2コア以上
