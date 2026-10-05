# CIで作った静的サイトを確認する

`client build`ワークフローは、viewerや関連コードがmainに反映されたとき、またはPRで変更されたときに静的サイトを作り、確認用のartifact（ダウンロードできるファイル一式）を7日間保存します。自分でNodeの環境を用意してビルドする必要はありません。画面にはリポジトリ内のテスト用レポートが入り、実環境のAPIやレポートは使用しません。

## ダウンロードと閲覧

1. GitHubにログインして[client buildの実行一覧](https://github.com/digitaldemocracy2030/kouchou-ai/actions/workflows/client-build.yml)を開きます。
2. mainの確認なら、対象コミットに対応する成功した実行を選びます。PRの場合は、そのPRのChecksから`client build`を開けます。
3. 実行のSummaryにあるArtifactsから`static-viewer-<commit SHA>`をダウンロードし、ZIPを展開します。
4. `index.html`があるフォルダーで、Pythonを使ってHTTPサーバーを起動します。

```bash
python3 -m http.server 3000 --bind 127.0.0.1
```

Windowsで`python3`が見つからない場合は、`py -m http.server 3000 --bind 127.0.0.1`を使います。Pythonの導入が必要です。

5. ブラウザで`http://localhost:3000/`を開き、一覧からテスト用レポートを選びます。終わったらターミナルでCtrl+Cを押します。

HTMLをダブルクリックして開く方法ではなく、HTTPサーバー経由で確認してください。`_next`などの付属フォルダーも必要です。

## どのコードを見ているか

同梱の`BUILD_COMMIT.txt`に、ビルドしたコミットのSHAがあります。PRのCIでは通常、PRとmainを組み合わせた検証用コミットであり、PRの先端SHAとは異なります。実行一覧のブランチ・コミット情報と併せて確認してください。

対象ファイルに変更がないコミットでは、このワークフローは自動実行されません。必要な場合は実行権限のある人がActionsの「Run workflow」から対象ブランチを選んで実行できます。保存期限が切れたartifactも、再実行して作り直せます。

このartifactは従来の`build:static`の出力です。shell方式は[別の開発ガイド](static-shell-export.md)を参照してください。GitHub Pages等への常設公開はまだ行いません。[Issue #518](https://github.com/digitaldemocracy2030/kouchou-ai/issues/518)のうち、ビルドの自動化と成果物の取得をこの仕組みで進め、常設URLでの閲覧は後続課題とします。
