# 広聴 AI / kouchou-ai

デジタル民主主義 2030 プロジェクトにおいて、ブロードリスニングを実現するためのソフトウェア「広聴 AI」のリポジトリです。

このプロジェクトは、[AI Objectives Institute](https://www.aiobjectivesinstitute.org/) が開発した [Talk to the City](https://github.com/AIObjectives/talk-to-the-city-reports)を参考に、日本の自治体や政治家の実務に合わせた機能改善を進めています。

- 機能例
  - 開発者以外でも扱いやすいような機能 (CSV Upload)
  - 濃いクラスタ抽出機能
  - パブリックコメント用分析機能（予定）
  - 多数派攻撃に対する防御機能（予定）

## 前提条件

- 一般ユーザー向け：
  - 安定版リリースをダウンロード（[Windows](./docs/windows-setup.md)/[Mac](./docs/mac-setup.md)/[Linux](./docs/linux-setup.md)の各ガイドを参照）
  - Docker（各ガイドに従ってインストール）
  - OpenAI API キー
- 開発者向け：
  - docker
  - git
  - OpenAI API キー

## セットアップ・起動

### 前提

- 広聴 AI は Web アプリとして構築されており、アプリケーションを立ち上げ、ブラウザを操作することでレポートの出力と閲覧ができます
- 以下の手順は、ローカル環境で docker compose を使用してセットアップする際の手順となります
- リモート環境でホスティングする場合は、個別のサービス（client, client-admin, api）について、適切に環境変数を設定した上でそれぞれホスティングしてください
  - サービスごとに設定する環境変数は.env.example に記載しています

### おすすめクラスタ数設定

レポート作成時の意見グループ数（クラスタ数）の目安は以下の通りです：

- コメント数の立方根（∛n）を基準として設定することをお勧めします
- 例：
  - 1000 件のコメント: 10→100（一層目 → 二層目）
  - 8000 件のコメント: 20→400
  - 125 件のコメント: 5→25
  - 400 件のコメント: 7→50
- デフォルト設定は上記に基づいて設定されますが、コメント数に応じて調整することで最適な分析結果が得られます

### 手順

- 開発者でない方は以下のユーザーガイドを参照してください：

  - [Windows 環境でのユーザーガイド](./docs/windows-setup.md)
  - [Mac 環境でのユーザーガイド](./docs/mac-setup.md)
  - [Linux 環境でのユーザーガイド](./docs/linux-setup.md)

- 開発者向け：
  - リポジトリをクローン
  - `cp .env.example .env` をコンソールで実行
    - コピー後に各環境変数を設定。各環境変数の意味は.env.example に記載。
  - `docker compose up` をコンソールで実行
    - ブラウザで http://localhost:3000 にアクセスすることでレポート一覧画面にアクセス可能
    - ブラウザで http://localhost:4000 にアクセスすることで管理画面にアクセス可能
    - 環境変数（.env）を編集した場合は、`docker compose down` を実行した後、 `docker compose up --build` を実行してアプリケーションを起動してください
      - 一部の環境変数は Docker イメージのビルド時に埋め込まれているため、環境変数を変更した場合はビルドの再実行が必要となります

### Google Analytics の設定

- Google Analytics 4（GA4）を使用して、ユーザーのアクセス解析を行うことができます
- 設定手順:
  1. Google Analytics アカウントを作成し、データストリームを設定して測定 ID を取得します（G-XXXXXXXXXX の形式）
  2. `.env` ファイルに以下の環境変数を設定します:
     - `NEXT_PUBLIC_GA_MEASUREMENT_ID`: クライアントアプリ（ポート 3000）用の測定 ID
     - `NEXT_PUBLIC_ADMIN_GA_MEASUREMENT_ID`: 管理画面アプリ（ポート 4000）用の測定 ID
  3. 本番環境（`ENVIRONMENT=production` または `NODE_ENV=production`）でのみ Google Analytics が有効になります
     - 開発環境では自動的に無効化されるため、開発中のアクセスはカウントされません

アプリ起動後の、アプリの操作方法については[広聴 AI の使い方](./how_to_use/README.md)を参照

### メタデータファイルのセットアップ

レポート作成者に関する情報（ロゴ画像やリンクなど）をカスタマイズするには、以下の手順で設定してください。

1. デフォルト環境について
   - デフォルト環境（`server/public/meta/default`）では、画像やリンクは表示されません
   - これはテスト環境用の設定であり、本番環境では使用しないでください

2. カスタマイズ方法
   - `server/public/meta/custom` ディレクトリに以下のファイルを配置することで、レポート作成者情報をカスタマイズできます：
     - `metadata.json`: レポート作成者の基本情報
     - `reporter.png`: レポート作成者のロゴ画像
     - `icon.png`: レポートのアイコン画像
     - `ogp.png`: レポートのOGP画像

3. 表示の条件
   - 画像の表示：`reporter.png`が`custom`ディレクトリに存在する場合のみ表示されます
   - リンクの表示：`metadata.json`の各リンク（webLink, privacyLink, termsLink）に値が設定されている場合のみ表示されます
   - 値が空の場合や、ファイルが存在しない場合は、該当する要素は表示されません

### Azure 環境へのセットアップ

Azure 環境にセットアップする方法は[Azure 環境へのセットアップ方法](./Azure.md)を参照

### 静的ファイル出力

レポートを閲覧する画面は、静的ファイルとしても出力できます。  
出力したファイルを Web サーバーに配置することで、アプリを起動せずにレポートを閲覧することが可能です。

静的ファイルを生成する場合は、以下のコマンドを実行してください。

```sh
make client-build-static
```

`out/` ディレクトリに静的ファイルが出力されますので、Web サーバーに配置してください。

## アーキテクチャ概要

本システムは以下のサービスで構成されています。

### api (server)

- ポート: 8000
- 役割: バックエンド API サービス
- 主要機能:
  - レポートデータの取得・管理
  - レポート生成パイプラインの実行
  - 管理用 API の提供
- 技術スタック:
  - Python (FastAPI)
  - Docker

### client

- ポート: 3000
- 役割: レポート表示用フロントエンド
- 主要機能:
  - レポートの可視化
  - インタラクティブなデータ分析
  - ユーザーフレンドリーなインターフェース
- 技術スタック:
  - Next.js
  - TypeScript
  - Docker

### client-admin

- ポート: 4000
- 役割: 管理用フロントエンド
- 主要機能:
  - レポートの作成・編集
  - パイプライン設定の管理
  - システム設定の管理
- 技術スタック:
  - Next.js
  - TypeScript
  - Docker

### utils/dummy-server

- 役割: 開発用ダミー API
- 用途: 開発環境での API モックとして使用

## client の開発環境の構築手順

フロントエンドのアプリケーション(client と client-admin) を開発用のダミーサーバ (dummy-server) をバックエンドとして起動する手順です。

### 1. client, client-admin, dummy-server の環境構築

```sh
make client-setup
```

### 2. 開発サーバーを起動

```sh
make client-dev -j 3
```

## 免責事項

大規模言語モデル（LLM）にはバイアスがあり、信頼性の低い結果を生成することが知られています。私たちはこれらの問題を軽減する方法に積極的に取り組んでいますが、現段階ではいかなる保証も提供することはできません。特に重要な決定を下す際は、本アプリの出力結果のみに依存せず、必ず内容を検証してください。

## 注意事項

本アプリは開発の初期段階であり、今後開発を進めていく過程で前バージョンと互換性のない変更が行われる可能性があります。
アプリをアップデートする際には、重要なデータ（レポート）がある場合はアプリ・データのバックアップを保存した上でアップデートすることを推奨します。

## 開発者向けのガイドライン

広聴 AI は OSS として開発されており、開発者の方からのコントリビュートを募集しています。
詳しくは、[CONTRIBUTING.md](CONTRIBUTING.md)を参照ください。
また、本プロジェクトでは AI エンジニア「[Devin](https://cognition.ai)」との協働開発を行っています。
現時点での Devin とのコラボレーションについては、模索中ですが [Devin とのコラボレーション](docs/DEVIN_COLLABORATION.md)を参照してください。

## 機能要望・バグ報告について

- github アカウントをお持ちの方は、[Issue](https://github.com/digitaldemocracy2030/kouchou-ai/issues) にバグ・改善要望を投稿してください
- github アカウントをお持ちでない方は、以下の google form よりバグ・改善要望を投稿してください
  - [バグ報告・改善要望フォーム](https://docs.google.com/forms/d/e/1FAIpQLSf43rpi8N1hGQmECDOBOmiV3c-Buwf4gWSj2sYc2KbZL9NOBA/viewform?usp=dialog)

## クレジット

このプロジェクトは、[AI Objectives Institute](https://www.aiobjectivesinstitute.org/) が開発した [Talk to the City](https://github.com/AIObjectives/talk-to-the-city-reports)を参考に開発されており、ライセンスに基づいてソースコードを一部活用し、機能追加や改善を実施しています。ここに原作者の貢献に感謝の意を表します。
