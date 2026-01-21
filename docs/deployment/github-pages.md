# GitHub Pagesの静的ファイルホスティング手順

このドキュメントでは、広聴AIで生成したレポートを静的エクスポートし、GitHub Pagesでホスティングする手順を説明します。

静的エクスポートを使用することで、サーバーサイドの処理を必要とせずに、静的なHTMLファイルとしてアプリケーションを配信できます。

## 1. GitHubリポジトリの作成

1. GitHubにログインし、新しいリポジトリを作成します（例: `kouchou-ai-reports`）
2. リポジトリを作成したら、ローカルにクローンします

```bash
git clone https://github.com/ユーザー名/kouchou-ai-reports.git
cd kouchou-ai-reports
```

## 2. 環境変数の設定

Next.js の静的エクスポートでは、公開先のパス（ルートかサブパスか）に応じて `NEXT_PUBLIC_STATIC_EXPORT_BASE_PATH` を設定します。

### リポジトリ用サイト（Project site）の場合
- ホスティング先が `https://<ユーザー名>.github.io/<リポジトリ名>/` のようにサブパスになる場合
- `.env` にリポジトリ名を `NEXT_PUBLIC_STATIC_EXPORT_BASE_PATH` として指定  

```.env
NEXT_PUBLIC_STATIC_EXPORT_BASE_PATH=/<リポジトリ名>
```

### ユーザー／組織用サイト（User/Organization site）の場合
- リポジトリ名が`<ユーザー名/組織名>.github.io`で、ホスティング先が `https://<ユーザー名>.github.io/` のようにルート直下になる場合  
- `NEXT_PUBLIC_STATIC_EXPORT_BASE_PATH` の設定は不要（未設定か空文字のままでOK。デフォルトで `/` が使われます）

```.env
NEXT_PUBLIC_STATIC_EXPORT_BASE_PATH=
```


## 3. 静的エクスポートの実行

**注意**: 静的エクスポートを行う前に、レポートを「公開」状態にする必要があります。

以下のコマンドを実行して、静的エクスポートを行います：

```bash
make client-build-static
```

このコマンドでビルド結果が`out`ディレクトリにコピーされます。

**注意**: `NEXT_PUBLIC_STATIC_EXPORT_BASE_PATH` を変更した際はビルドが必要です。以下のコマンドでビルドしたうえで静的エクスポートしてください。

```bash
make build && make client-build-static
```


## 4. 静的ファイルのデプロイ

### 4.1 ビルド結果のコピー

`out`ディレクトリに生成されたファイルを、GitHubリポジトリのクローンしたディレクトリにコピーします：

```bash
# ビルド結果をコピー
cp -r out/. /path/to/kouchou-ai-reports/
```

**注意**: `out`ディレクトリは毎回のビルドで削除されるため、`.git`ディレクトリも削除されてしまいます。そのため、別のディレクトリにリポジトリをクローンしておき、そこにビルド結果をコピーする方法を推奨します。

### 4.2 GitHubへのプッシュ

コピーしたファイルをGitHubにプッシュします：

```bash
cd /path/to/kouchou-ai-reports
git add .
git commit -m "Update static files"
git push origin main
```


## 5. GitHub Pagesの設定

1. リポジトリの「Settings」タブを開きます
2. 左側のメニューから「Pages」を選択します
3. 「Source」セクションで、以下のように設定します：
    - Branch: `main`
    - Folder: `/(root)`
4. 「Save」ボタンをクリックします


## 6. デプロイの確認

プッシュが完了すると、GitHub Actionsによってデプロイが実行されます。デプロイが完了したら、以下のURLでアクセスできます：

```
https://<ユーザー名>.github.io/kouchou-ai-reports/
```
