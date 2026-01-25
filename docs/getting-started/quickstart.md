# クイックスタート

このガイドでは、広聴AIを最短で使い始めるための手順を説明します。

## 前提条件

- **Docker**: Docker Desktop または Docker Engine がインストールされていること
- **OpenAI API キー**: レポート生成に必要です（ローカルLLM使用時は不要）

!!! tip "OS別の詳細なセットアップ"
    詳細なセットアップ手順は各OS向けガイドをご覧ください：

    - [Windows セットアップ](windows-setup.md)
    - [Mac セットアップ](mac-setup.md)
    - [Linux セットアップ](linux-setup.md)

## 開発者向けクイックスタート

### 1. リポジトリをクローン

```bash
git clone https://github.com/digitaldemocracy2030/kouchou-ai.git
cd kouchou-ai
```

### 2. 環境設定

```bash
cp .env.example .env
```

`.env` ファイルを編集して、以下の項目を設定します：

```ini
# 必須: OpenAI API キー
OPENAI_API_KEY=sk-your-api-key-here

# オプション: 環境設定
ENVIRONMENT=development
```

### 3. アプリケーションの起動

```bash
docker compose up
```

初回起動時は Docker イメージのビルドに数分かかります。

### 4. アクセス

起動完了後、ブラウザで以下の URL にアクセスできます：

| サービス | URL | 説明 |
|---------|-----|------|
| レポート一覧 | http://localhost:3000 | 生成されたレポートを閲覧 |
| 管理画面 | http://localhost:4000 | レポートの作成・管理 |
| API | http://localhost:8000 | バックエンド API |

## 基本的な使い方

### レポートの作成

1. http://localhost:4000 にアクセス
2. 「新規レポート作成」をクリック
3. CSV ファイルをアップロード（コメントデータ）
4. 設定を調整して「レポート生成」を実行
5. 生成完了後、http://localhost:3000 でレポートを確認

### CSV ファイルの形式

```csv
comment-body
これは最初のコメントです。
これは2番目のコメントです。
意見が含まれるテキストをここに入力します。
```

!!! info "おすすめのクラスタ数設定"
    コメント数の立方根（∛n）を基準に設定することをお勧めします：

    | コメント数 | 一層目 | 二層目 |
    |-----------|-------|--------|
    | 125件 | 5 | 25 |
    | 400件 | 7 | 50 |
    | 1000件 | 10 | 100 |
    | 8000件 | 20 | 400 |

## 次のステップ

- [使い方の詳細](../user-guide/how-to-use.md)
- [CLI からの実行](../user-guide/cli-quickstart.md)
- [Azure へのデプロイ](../deployment/azure.md)

## トラブルシューティング

### Docker が起動しない

Docker Desktop が起動しているか確認してください。

```bash
docker --version
docker compose version
```

### API キーのエラー

`.env` ファイルの `OPENAI_API_KEY` が正しく設定されているか確認してください。

### ポートが使用中

他のアプリケーションが同じポートを使用している場合は、該当するアプリケーションを停止するか、`.env` でポート番号を変更してください。
