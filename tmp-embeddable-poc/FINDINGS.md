# Python embeddable パッケージング PoC — 検証結果

日付: 2026-06-01 / 対象: kouchou-ai を Windows スタンドアロン化（embeddable Python 方針）

## 結論

**embeddable Python 方針は成立する。** 最大リスクだった numba/UMAP の JIT、
パイプラインの subprocess 起動、FastAPI+uvicorn の Web 配信がすべて 1 つの
embeddable Python 上で動いた。**torch は不要**（LM Studio の embedding を使う前提）。

## 構成

- Python 3.12.10 embeddable (amd64) を `runtime/` に展開
- `python312._pth` を編集して `Lib\site-packages` を追加 + `import site` を有効化
- `get-pip.py` で pip をブートストラップ
- `analysis-core[clustering,gemini]`（torch を含む `embeddings` は入れない）+
  `uvicorn[standard] fastapi pydantic-settings orjson structlog` を導入

### embeddable 特有のハマりどころ（重要）

`pip install ./packages/analysis-core` がビルド分離で `hatchling.build` を import
できず失敗する。embeddable の `_pth` がビルド用サブプロセスの sys.path を絞るため。

**回避策**: 先に `pip install hatchling` してから `--no-build-isolation` を付けてインストール。
（本番ビルドスクリプトでは、システム Python で analysis-core の wheel を事前ビルドし、
その wheel を embeddable に入れる方が確実。）

## スモークテスト結果（すべて PASS）

| 検証項目 | 結果 |
|---|---|
| numba `@njit` のコンパイル+実行 | OK |
| UMAP `fit_transform`（numba 内部を実走） | OK shape=(200,2) |
| polars / scipy / sklearn import | OK |
| `python -m analysis_core --help` | OK（CLI 起動成功） |
| uvicorn で FastAPI 起動 + `/health` | OK |
| FastAPI `StaticFiles` で index.html 配信 | OK（= Next 静的配信の裏付け） |
| `sys.executable` が embedded python.exe を指す | OK |

### 起動コスト（体感の論点）

- 初回 cold import（numba/llvmlite/umap など）: **約 20 秒**
- 初回 UMAP fit（UMAP 内部の numba JIT 含む）: **約 8.6 秒**
- いずれも JIT キャッシュが効く 2 回目以降は短縮される。初回起動だけ「重い」点は
  スプラッシュ表示などで吸収する想定。

## 配布サイズ

- `runtime/` 合計: **約 664MB**（pip ~12MB を除けば実質 ~650MB）
- 内訳上位: polars ランタイム 175M / scipy 117M / llvmlite 104M / sklearn 43M /
  numpy 33M / numba 30M
- 参考: `torch` を入れていたら +2.5GB 超だった。**LM Studio 委譲で回避できている。**
- 圧縮インストーラ（Inno Setup/NSIS）にすれば配布物は ~250-300MB 程度の見込み。

## 本実装で必要な改修（最小）

1. **`report_launcher._build_analysis_core_command` の `"python"` を `sys.executable` に変更。**
   現状 PATH 上の `python` を拾うため、embeddable では同梱インタプリタを呼べない。
   - `apps/api/src/services/report_launcher.py:70`
2. embedding 経路を `provider="local"`（LM Studio の OpenAI 互換 embedding）に寄せ、
   `request_to_local_embed`（= torch フォールバック）に落ちない設定にする。
   - フォールバックすると torch が必要になり、サイズ削減が台無しになる。

---

# 第2フェーズ検証（end-to-end / 実 API / フロント静的化）

## 1. numba 系パイプライン本体の実行（実関数）

合成データ（3 latent group × 20 = 60 args, 256 次元）で
`hierarchical_clustering` ステップを実関数で実行 → **PASS**。
- UMAP fit → KMeans(9) → scipy ward linkage → fcluster(3) → CSV 出力まで完走
- 出力: 60 行、level-1 が 3 クラスタ / level-2 が 9 クラスタ、x/y 座標付き
- 所要 23.8 秒（大半は初回 numba JIT）
- → **numba 系の本丸が embeddable 上で実データで動くことを確認**

## 2. 全ステップ/オーケストレータの import

extraction / embedding / clustering / labelling×2 / overview / aggregation /
visualization / layout_generation / orchestrator / workflow / workflows の
**12 モジュールすべて import 成功**（plotly 等の追加ネイティブ依存も不足なし）。

## 3. 実 API アプリ（apps/api `src.main:app`）の起動 — 重大な発見

embeddable の uvicorn で実 API を起動したところ、**全 import は成功し起動シーケンスまで
到達したが、lifespan で `UnicodeDecodeError: 'cp932' codec` が出て起動失敗**。

- 原因: 日本語 Windows のデフォルト文字コードが **cp932 (Shift-JIS)**。
  `json.load(open(path))` 等の `encoding` 未指定の読み込みが UTF-8 の JSON を
  cp932 で開こうとして死ぬ。Docker/Linux は UTF-8 既定なので顕在化しない。
  - 例: `apps/api/src/services/report_status.py:45` の `json.load(f)`
- **解決策（確認済み）: 起動時に `PYTHONUTF8=1` を設定すると一括解決。**
  - `PYTHONUTF8=1` を付けて再起動 → 起動完了。`/openapi.json`=200、
    `/meta/metadata.json`=200 で日本語 JSON（「名前未設定ユーザー」）も正しく返却。
- **→ スタンドアロンのランチャーは必ず `PYTHONUTF8=1` を設定すること。**
  （または全 `open()`/`json.load()` に `encoding="utf-8"` を付与。ランチャー側の
  環境変数 1 行が圧倒的に低コスト。）

## 4. フロントエンドの静的配信可否

| アプリ | 設定 | 静的化 | スタンドアロンでの扱い |
|---|---|---|---|
| **public-viewer** | `NEXT_PUBLIC_OUTPUT_MODE=export` で `output:"export"` | **可能** | ビルド済み静的ファイルを FastAPI `StaticFiles` で配信 ✅ |
| **admin** | `output:"standalone"` + **Server Actions 使用** | **不可** | **Node.js ランタイムが必須** ❌ |

- public-viewer はレポート閲覧側。静的配信で問題なし（既存 static-site-builder と同じ経路）。
- admin はレポート作成 UI。Server Actions のため純静的化できず、以下のどちらかが必要:
  - (a) **Node.js を同梱**して admin の standalone サーバ（`node server.js`）を起動する
  - (b) admin の Server Actions を FastAPI 呼び出しに書き換えて静的エクスポート可能にする

## まとめ：スタンドアロン構成の現実像

```text
[インストーラ (Inno Setup/NSIS)]
 ├─ runtime/           … embeddable Python + FastAPI + pipeline（検証済み・~650MB）
 │    └─ launcher が PYTHONUTF8=1 を設定して uvicorn 起動（必須）
 ├─ public-viewer/     … 静的エクスポート済みファイル（FastAPI から配信）
 ├─ admin/             … ★Node.js ランタイム必須（同梱 or 書き換えが要判断）
 └─ (別途) LM Studio   … ローカル LLM（chat + embedding を委譲。torch 回避の前提）
```

---

# 第3フェーズ：public-viewer のスタンドアロン SPA 化（完了・実機検証済み）

## 目的

static export は本来「ビルド時のレポートを焼き込む」方式（static-site-builder 用途）で、
実行時に作成したレポートを表示できない（slug 焼き込み・0件だとビルド失敗）。
スタンドアロンでは利用者が実行時にレポートを作るため、**クライアント SPA 化**して
実行時に API から取得・描画する方式にした。ホスト版(SSR)と static-site-builder は不変。

## 実装（すべて `isStandaloneBuild()` = `NEXT_PUBLIC_STANDALONE=1` で分岐）

- `app/utils/static-build.ts`: `isStandaloneBuild()` を追加（export とは別フラグ）。
- `components/report/ReportView.tsx`: slug を受け取り実行時に `/reports/{slug}` を取得して描画するクライアント版（新規）。
- `app/report/page.tsx`: `?slug=` を読む universal ページ。`dynamic(ssr:false)` でクライアント専用描画。
- `app/ReportListClient.tsx` + `app/StandaloneListPage.tsx`: 一覧をクライアント取得し `/report?slug=` へリンク。
- `app/[slug]/page.tsx`: standalone 時は sentinel を1つだけ生成し、サーバ fetch せず `StandaloneSlugView` を描画。
- `components/reporter/ReporterClient.tsx`: `Reporter` のクライアント版（新規、下記 #482 対策）。
- 配信: FastAPI が `/viewer` で静的配信（API が `/` を持つため basePath=`/viewer`）。`run-server.py` がマウントしブラウザを `/viewer/` で開く。
- ビルド: `build.ps1` が `NEXT_PUBLIC_OUTPUT_MODE=export NEXT_PUBLIC_STANDALONE=1 NEXT_PUBLIC_API_BASEPATH=（空） NEXT_PUBLIC_PUBLIC_API_KEY=local-public NEXT_PUBLIC_STATIC_EXPORT_BASE_PATH=/viewer` で `out/` を生成し `dist/viewer` へ。

## 検証（Playwright・実バンドル）

- 一覧ページ：ヘッダー/レポーター/フッター描画、公開レポートのカード（タイトル「あああ」+作成日時）表示。
- カードクリック → `/viewer/report/?slug=...` 遷移 → レポート全描画（概要文 + チャート要素 54個=Plotly散布図・日本語クラスタラベル）。
- すべて静的ファイル + embeddable API から実行時取得。Node 不要。スクショ: `FINAL-list.png` / `FINAL-report.png`。

## ハマりどころ（次回のために記録）

- **React #482（致命的）**: `Reporter` が async サーバコンポーネント。クライアントツリー内で描画すると落ちる → `ReporterClient` を作成して差し替え。
- **React #418（非致命）**: アプリ全体のハイドレーション不一致警告（未変更の faq でも出る）。standalone 入口は `dynamic(ssr:false)` で実害回避。
- **`output:export` の動的ルート**: 空 `generateStaticParams` はエラー。sentinel を1件返して回避。
- **`.env.local` 上書き**: 開発用 `apps/public-viewer/.env.local` が `NEXT_PUBLIC_API_BASEPATH` を上書きし、クライアントが別ポート(8002)を叩いて CORS 失敗。standalone はコード側で base を空（同一オリジン相対）に固定して回避。
- **`/reports` は public のみ**: 一覧 API は `is_publicly_visible`（visibility=public）でフィルタ。unlisted は個別リンクのみ閲覧可。検証時は1件を public にして確認。
- **basePath `/viewer`**: API が `/`(healthcheck) を持つため衝突回避でサブパス配信。
- **trailingSlash**: リンクは `/viewer/report/?slug=` になる。
- **Copy-Item ネスト**: 既存同名ディレクトリへ `Copy-Item -Recurse` すると `broadlistening/broadlistening/...` とネストし古いデータが残る → コピー前に `$AppDir` を削除。
- **PowerShell 5.1 のネイティブ stderr**: `next build` の警告 stderr が `$ErrorActionPreference=Stop` で致命化 → フロントビルド区間だけ `Continue` にし `$LASTEXITCODE` で判定。
- **git-bash の MSYS パス変換**: 検証時 `/viewer` が `C:/Program Files/Git/viewer` に化ける（`MSYS_NO_PATHCONV=1` で回避）。PowerShell の build.ps1 では発生しない。

## zip 配布可否（この時点）

- バンドルは再配置可能（絶対パス焼き込み無し）で、解凍先自由・`start.bat` で起動。
- build.ps1 はレポートデータを空にして同梱（私的データ漏洩・肥大化を回避）。
- **public-viewer 同梱済みなので、zip で「一覧→レポート閲覧」まで成立**（レポート作成 UI=admin はまだ Node 必要・未同梱）。
- 配布前の注意: 未署名 zip の SmartScreen/Defender 摩擦、浅いパスへの解凍推奨、LM Studio 別途必要。

## 残タスク / 要判断

- **admin をどうするか**（Node 同梱 vs Server Actions 書き換え）が最大の分岐点。
  これが決まらないと「単一 Python ランタイムで完結」にはならない。
- ランチャー exe（PYTHONUTF8=1 設定 + API 起動 + ブラウザ自動オープン）＋ Inno Setup 化。
- 本番ビルドでは analysis-core を wheel 事前ビルドして embeddable に入れる
  （`--no-build-isolation` 依存を排除）。
- 実 LLM での真の end-to-end は LM Studio を GUI 起動した状態でユーザー自身が要実施
  （本 PoC 環境では headless 起動できず未実施。LLM 経路自体は OpenAI 互換 HTTP で
  embeddable 固有リスクは無い）。
