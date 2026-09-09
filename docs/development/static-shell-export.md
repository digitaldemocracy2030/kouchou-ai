# shell配布物の組み立て

shell方式は画面をリリース時に一度ビルドし、レポート出力時には共通assetsと公開用JSONから配布物を作ります。従来の`static-site-builder`の`/build`は変更していません。この方式は明示的に選んで使うもので、FastAPIのダウンロード経路への接続は#885の後続作業です。

## 画面の事前ビルド（開発・リリース時）

```sh
pnpm --filter @kouchou-ai/public-viewer build:shell
```

`apps/public-viewer/out`を未加工の共通assetsとして保存します。配下パスで配信する場合はビルド時に`NEXT_PUBLIC_STATIC_EXPORT_BASE_PATH`を設定します。レポートの追加・変更でこのビルドを繰り返す必要はありません。

## Pythonで組み立てる（レポート出力時）

入力ディレクトリは次の構成です。各JSONの形は公開APIの`/meta/metadata.json`、`/reports`、`/reports/{slug}`と同じです。

```text
export-data/
  metadata.json
  reports.json
  reports/
    example.json
```

限定公開レポートを含める場合は、選択したレポートの記述を`reports.json`に加え、本文にも`visibility: "unlisted"`を含めます。公開APIの通常の一覧には限定公開レポートが含まれない点に注意してください。組立処理はAPIに接続せず、入力済みのJSONを使います。

```sh
python3 apps/api/src/services/shell_export.py \
  --assets apps/public-viewer/out \
  --data export-data \
  --output packaged-site
```

Python標準ライブラリだけで動作し、組立時のNodeやAPIキーは不要です。`package_shell`関数をFastAPIなどから呼ぶこともできます。出力先はassetsの外側にある新しいディレクトリを指定します。古いレポートが残らないよう、既存の配布物への上書きは受け付けません。

- 各レポートHTMLに「質問 - レポーター」のタイトルをHTMLエスケープして挿入します。
- 限定公開には`noindex, nofollow`を最初から含めます。公開には`index, follow`を設定します。
- 限定公開は配布物内の一覧にも載せません。privateや公開状態の不整合はエラーにします。
- ブラウザで一覧・詳細を移動した場合も同じタイトルとrobotsを設定します。検索除外はJavaScriptの実行だけには依存しません。

## 閲覧・公開

```sh
python3 -m http.server 3000 --bind 127.0.0.1 --directory packaged-site
```

ローカル閲覧はこのHTTPサーバーで行います。Web公開する場合は配布物全体を配置してください。`noindex`は検索エンジン向けの指示で、閲覧制限・認証の代わりにはなりません。OGP画像の生成はこの処理の対象外です。

#939は#935作者が挙げたレポート別title / noindexの制約への対応です。E2Eの`package-shell.mjs`はfixtureを用意するアダプターであり、実際の組立処理には上のPython実装を使います。
