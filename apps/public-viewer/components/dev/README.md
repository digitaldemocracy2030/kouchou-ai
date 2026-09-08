# Viewer状態カタログ

public-viewerの開発サーバーで `/dev/viewer-states/` を開く。API・ダミーサーバー・キーは不要。通常、レポート0件、メタデータなし、接続エラー、属性なし、空の意見、明示的な散布図を切り替える。通常状態ではフィルターのテキスト検索で該当0件も作れる。

実際の一覧・レポーター・エラー・レポートコンポーネントを使用する。本番buildでは404にする。Storybookや外部ホスティングを新たに導入せず、まず既存Next.jsで状態比較を可能にした。

viewer-fixture.jsonはserverlessの公開sample-report.json（仮想アンケート）から先頭12意見と対応クラスタを抜き出し、件数を再計算したもの。個人の入力・実API結果ではない。両版の比較にもこのファイルを使う。ブラウザのレスポンシブ表示で390px / 1280pxを比較する。

自動検査: `cd test/e2e && pnpm exec playwright test -c playwright.viewer-states.config.ts`。API非依存のカタログを使い、状態切替・全画面の領域分離・スマホ初期表示と明示設定を検査する。
