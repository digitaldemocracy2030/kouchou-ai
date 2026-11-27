# Viewer状態カタログ

public-viewerの開発サーバーで `/dev/viewer-states/` を開く。API・ダミーサーバー・キーは不要。通常、レポート0件、メタデータなし、接続エラー、属性なし、空の意見、明示的な散布図を切り替える。通常状態ではフィルターのテキスト検索で該当0件も作れる。

実際の一覧・レポーター・エラー・レポートコンポーネントを使用する。本番buildでは404にする。Storybookや外部ホスティングを新たに導入せず、まず既存Next.jsで状態比較を可能にした。

viewer-fixture.jsonはserverlessの公開sample-report.json（仮想アンケート）から先頭12意見と対応クラスタを抜き出し、件数を再計算したもの。個人の入力・実API結果ではない。両版の比較にもこのファイルを使う。ブラウザのレスポンシブ表示で390px / 1280pxを比較する。

自動検査: `cd test/e2e && pnpm exec playwright test -c playwright.viewer-states.config.ts`。API非依存のカタログを使い、状態切替・全画面の領域分離・スマホ初期表示と明示設定を検査する。

## 散布図の輪郭比較

`/dev/scatter-outlines/` で、同梱の 9,568 点の例を使い、元の凸包が重なった組を選び、調整前と調整後を同じ範囲で拡大比較する。点線は元の重なりを示す。2 種類のクラスタ分けを選べる。「全体表示で見る」ではレポート全体で描画方式を切り替える。

```sh
# public-viewer ディレクトリで開発サーバーを起動
pnpm exec next dev --webpack -H 127.0.0.1 -p 41261

# 別ターミナルでリポジトリルートから計測
node apps/public-viewer/scripts/benchmark-scatter-outlines.mjs /tmp/scatter-outline-measurements
```

Playwright に入れた Chromium を使う。任意の Chrome で測る場合は実行ファイルを `SCATTER_OUTLINE_CHROME` に指定する。各方式を同じ点群・画面サイズで交互に 20 回ずつ測り、輪郭計算、`Plotly.newPlot`、`Plotly.relayout` の時間とスクリーンショットを保存する。`SCATTER_OUTLINE_COMPARE_VORONOI=1` を付けると、局所ボロノイを含む 3 方式を測る。`SCATTER_OUTLINE_CPU_RATE=4` で狭いビューポートと CPU スロットリングを組み合わせて比較できる。

安全に切れない重なりは表示に残る。切り抜いた輪郭は穴を描ける Plotly の shape を使うため、切り抜いた塗り面のホバーに反応しない。点のホバーと色、座標は同じ散布図コンポーネントで扱う。
