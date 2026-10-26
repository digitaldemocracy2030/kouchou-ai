# Web UI の runtime Node 依存インベントリ（#885 完了条件 第1項）

`apps/admin` / `apps/public-viewer` / `apps/static-site-builder` を読み、**Node.js runtime（Next.js のサーバ実行層 / Express）に依存している箇所**を網羅しました。各行は実コード根拠です。初版は `d5c9ece` 時点。2026-10-26 に全体を `b70125d` 時点の `main`（#1132・#1136 の merge 後）と照合し、行番号と本数を更新しました。

## 結論（先に）

- **`apps/admin`**: Node runtime 依存はほぼ「FastAPI への薄い proxy」と「static export を阻害する設定」だけ。**ファイル生成 / zip / build を行う箇所は 0**。Node 固有の API を使うのは、`/api/download` が static-site-builder を `node:http(s)` で呼んで ZIP をストリーム中継する箇所（#1125）、CSV / JSON ダウンロードの Server Action が応答を `Buffer` で base64 化する箇所、middleware が Basic 認証のヘッダーを `Buffer` でデコードする箇所、instrumentation が起動時に `node:fs` で `.env` を診断する箇所の 4 つ。→ client fetch + `output:"export"` 化で runtime Node をほぼ外せる（残課題は API key の threat model と、`/api/download` の中継先）。
- **`apps/public-viewer`**: 既に `NEXT_PUBLIC_OUTPUT_MODE=export` モードを持ち、**runtime の Node 依存（ISR / `connection()` / server fetch）は export ビルドで build 時処理に倒れて解決済**。残るのは「export ビルドそのものに Node + Next + API 到達が必要」という **build 時依存**。
- **`apps/static-site-builder`**: ⭐ **単一exe化の最大の障壁**。`/build` を叩くたびに **runtime で `next build`（`pnpm run build:static`）を子プロセス実行**して `out/` を zip 返却する設計。「静的ファイルを生成する行為そのもの」が runtime の Node/Next build に依存している。

つまり #885 で本当に解くべきは admin の proxy 置換（容易）ではなく、**static-site-builder の runtime build をどう runtime から外すか**（事前ビルド成果物の配布 or Python 側での静的レポート生成）です。

---

## 1. `apps/admin`（Next.js 管理画面）

### 1-1. Server Actions（11 ファイル・計 16・全て FastAPI proxy）

| ファイル | action | 内容 | 除去難易度 |
|---|---|---|---|
| `_components/ReportCard/ActionMenu/csvDownloadCommon.ts` | `csvDownloadCommon` | `/admin/comments/{slug}/csv` GET proxy。応答を `Buffer` で base64 化して返す（`csvDownload.ts` / `csvDownloadForWindows.ts` から呼ばれる）。`csvDownloadForWindows` のとき（`includeBOM: true`）は、応答をテキストにして先頭に BOM（`\uFEFF`）を付けてから base64 化する | 低 |
| `_components/ReportCard/ActionMenu/jsonDownload.ts` | `jsonDownload` | `/admin/reports/{slug}/json` GET proxy。応答を `Buffer` で base64 化して返す | 低 |
| `_components/ReportCard/ClusterEditDialog/actions.ts` | `fetchClusters`, `updateCluster` | `/admin/reports/{slug}/cluster-labels` GET, `/cluster-label` PATCH の proxy | 低 |
| `_components/ReportCard/DeleteDialog/action.ts` | `reportDelete` | `/admin/reports/{slug}` DELETE proxy | 低 |
| `_components/ReportCard/DuplicateReportDialog/actions.ts` | `duplicateReport` | `/admin/reports/{slug}/duplicate` POST。**`process.env.ADMIN_API_KEY`（非PUBLIC）使用**（未設定なら例外）。再実行するステップで使うユーザー入力の API キーを、本文ではなく `x-user-api-key` ヘッダーで中継する（`redirect: "error"`） | 中（key 露出判断） |
| `_components/ReportCard/ReportEditDialog/actions.ts` | `updateReportConfig` | `/admin/reports/{slug}/config` PATCH proxy | 低 |
| `_components/ReportCard/Visibility/actions.ts` | `updateReportVisibility` | `/admin/reports/{slug}/visibility` PATCH proxy | 低 |
| `_components/ReportCard/VisualizationConfigDialog/actions.ts` | `fetchVisualizationConfig`, `updateVisualizationConfig` | `/admin/reports/{slug}/visualization-config` GET/PATCH proxy | 低 |
| `create/api/createReport.ts` | `createReport` | `/admin/reports` POST（コメント全件 body）。`serverActions.bodySizeLimit:"100mb"` 前提（§1-4）。ユーザー入力の API キーを `x-user-api-key` で中継する（`redirect: "error"`） | 中（大容量 POST + CORS） |
| `create/api/plugins.ts` | `getPlugins`, `validatePluginSource`, `previewPluginData`, `importPluginData` | `/admin/plugins` 系 GET/POST 4本 proxy | 低 |
| `create/components/EnvironmentCheckDialog/verifyApiKey.ts` | `verifyApiKey` | `/admin/environment/verify` GET proxy。ユーザー入力の API キーを `x-user-api-key` で中継する（`redirect: "error"`） | 低 |

すべて `getApiBaseUrl()` + `x-api-key` で内部 API を中継するだけ（`csvDownloadCommon` / `jsonDownload` は加えて応答を base64 文字列に変換）。サーバ専用シークレットを使うのは `duplicateReport`（`ADMIN_API_KEY`）のみ、他の 15 本は `NEXT_PUBLIC_ADMIN_API_KEY`（client 露出可）。ユーザー入力の API キーを中継するのは `createReport` / `duplicateReport` / `verifyApiKey` の 3 本で、どれも `x-user-api-key` ヘッダーで送り、リダイレクト先へ鍵を転送しないよう `redirect: "error"` を付けている。

初版のこの表は `ActionMenu/` の 2 ファイル（`csvDownloadCommon.ts` / `jsonDownload.ts`）を漏らしていた（どちらも `d5c9ece` 時点で存在）。追記し、§1-5・§4 の本数も合わせて訂正した。また、どこからも呼ばれていなかった `verifyChatGptApiKeyWithProvider`（中継先の `/admin/environment/verify-chatgpt` は API に存在しない）は削除したので、一覧と本数から外した。

### 1-2. Route Handlers（3本）

| route | 役割 | 種別 | 使用 env |
|---|---|---|---|
| `app/api/download/route.ts` (POST) | body の `slugs` を `${CLIENT_STATIC_BUILD_BASEPATH}/build` に POST し、返ってきた zip ストリームを `Content-Disposition: attachment; filename=kouchou-ai-<JST>.zip` で中継。builder はビルドが終わるまで応答しないので、global fetch（undici の headersTimeout 300 秒）ではなく `node:http(s)` で呼び（`requestStaticBuild.ts`、#1125）、無通信の待ち時間の上限（既定 30 分）を超えたら 504、接続できなければ 502 の JSON を返す | ストリーム中継 + ファイル名生成（**Node固有**：`node:http` / `node:https` / `node:stream`） | `CLIENT_STATIC_BUILD_BASEPATH`, `CLIENT_STATIC_BUILD_TIMEOUT_SECONDS`（任意） |
| `app/api/admin/reports/[slug]/config/route.ts` (GET) | `/admin/reports/{slug}/config` 中継。**`ADMIN_API_KEY` をブラウザに出さないための proxy 層**。`reuse/[slug]/page.tsx` と `DuplicateReportDialog.tsx` の client fetch が経由 | proxy | `ADMIN_API_KEY`, `API_BASEPATH ?? NEXT_PUBLIC_API_BASEPATH` |
| `app/api/healthcheck/route.ts` (GET) | `{status:"ok"}` を返すだけ。middleware の Basic 認証を bypass する対象 | 静的応答 | なし |

### 1-3. Server-side data fetch（static export 阻害）

- `app/page.tsx`: **Server Component で `fetch(${apiUrl}/admin/reports, { cache:"no-store" })`** を server 実行（`x-api-key` 付与）。`no-store` ＝ 完全動的レンダリングで `output:"export"` を直接阻害。**admin で server fetch しているのはここ 1本のみ**。
- `reuse/[slug]/page.tsx` / `create/page.tsx` は `"use client"`（初期 server fetch なし）。`layout.tsx` は server fetch なし（`process.env` を build/SSR 参照のみ）。

### 1-4. middleware / next.config / instrumentation

- **`middleware.ts`**: Basic 認証（`BASIC_AUTH_USERNAME` / `PASSWORD` が両方とも空でないときだけ有効）。`Authorization` のスキームが `Basic` で値があるときだけ `Buffer.from(...,"base64")` でデコードし、最初の `:` でユーザー名とパスワードに分けて比較する（パスワードに `:` を含められる。#1132）。一致しなければ、ヘッダーが無い・不正な場合も含めて 401。`/api/healthcheck` は無条件 bypass。→ middleware は `output:"export"` で**使用不可**（Next がエラー）。
- middleware は全パスで走り、Next はそのためにリクエスト本文を複製して `proxyClientMaxBodySize`（既定 10MB）で切り詰める。`createReport` の大きな本文が途中で切れないよう、`next.config.ts` で `proxyClientMaxBodySize` を `bodySizeLimit` より 1mb 大きい `"101mb"` にしている（値は `app/utils/requestBodyLimit.ts` の定数。#1124）。作成画面は送信前に本文の大きさを見積もり、上限（100MB）を超えるときは送らずにトーストで案内する。
- **`next.config.ts`**: `output:"standalone"`（**export ではない＝最大の阻害設定**）。`async headers()` で全パスに CSP 付与（実体は `apps/shared/csp.ts` の `buildCspHeaderValue()`：`default-src 'self'` 基調、GA 有効時に googletagmanager 等を追加）。`experimental.serverActions.bodySizeLimit:"100mb"` と `experimental.proxyClientMaxBodySize:"101mb"`（上記）。
- **`instrumentation.server.ts`**: `node:fs`（`readFileSync`/`existsSync`）+ `node:path` を直 import し、起動時に `.env` の override 診断を `console.warn`（機能本体ではなく開発支援）。`instrumentation.ts` は `NEXT_RUNTIME==="nodejs"` ガード付き。

### 1-5. admin の除去難易度マップ

| 依存 | 難易度 | 方針 |
|---|---|---|
| `NEXT_PUBLIC_ADMIN_API_KEY` を使う Server Action 15本（`duplicateReport` 以外） | 低 | 両モードで動く client API モジュールへ置換（CSV / JSON ダウンロードは、client が FastAPI の応答を `response.blob()` で直接受け取り、base64 の往復をなくす。Windows 向け CSV の BOM は client 側で付ける）。`createReport` は Server Action の本文上限（100MB）と `proxyClientMaxBodySize` から外れる。FastAPI 側には本文の上限が無いので、送信前の見積もりによる上限の検査は client に残す |
| `duplicateReport` / `config` route（`ADMIN_API_KEY`） | 中 | local desktop の threat model で client 露出許容 or FastAPI 直 |
| `healthcheck` route | 低 | export で不要化 |
| `page.tsx` server fetch | 中 | client fetch + loading 化 |
| `download` route（zip 中継） | 中 | static-site-builder を直接叩く / FastAPI 移管（§3 と連動） |
| `output:standalone` / CSP / Basic 認証（middleware）/ `proxyClientMaxBodySize` / instrumentation `node:fs` | 設定 | export 化、CSP は静的ホスト or Python 側、Basic 認証は local 不要（middleware が無くなれば本文の複製と `proxyClientMaxBodySize` も不要）、instrumentation は export 時除外可 |

---

## 2. `apps/public-viewer`（Next.js 公開レポート閲覧）

既に `NEXT_PUBLIC_OUTPUT_MODE === "export"` トグル（`next.config.ts`）と `app/utils/static-build.ts` の `isStaticExportBuild()` を持ち、**export 阻害要因はフラグ分岐で無効化済み**。

### 2-1. Route Handlers

| route | 役割 | 種別 | 使用 env |
|---|---|---|---|
| `app/api/revalidate/route.ts` (POST) | `{tag, secret}` を検証し `revalidateTag(tag, { expire: 0 })`（非公開化・削除の直後に古いページを返さないよう、stale-while-revalidate ではなく即時に失効させる） | **Node固有（ISR）**。`output:"export"` 下では成立しない | `REVALIDATE_SECRET` |
| `app/[slug]/opengraph-image.png/route.ts` (GET) | `_op-image.tsx` の `OpImage(slug)` を呼ぶ OGP 画像 route。**ただし `build` / `build:static` / `build:shell` のどれでもビルド対象から外れる**（通常のビルドでは `route.ts` を、export ビルドではディレクトリごと改名する。後述）。SSR モードの OGP 画像は、同じ `OpImage` を呼ぶ `app/[slug]/opengraph-image.tsx` が出す | **Node固有（`next/og`）** | `NEXT_PUBLIC_PUBLIC_API_KEY` 経由 |

### 2-2. runtime Node 依存 → export で解決済（SSR モード専用に残存）

- **ISR / revalidate**: `app/[slug]/page.tsx:24` `export const revalidate = 300`、`app/page.tsx:11` 同。`fetch(..., { next:{ tags:["meta"] } })` 等のタグ付きキャッシュ + `api/revalidate` の `revalidateTag` がペア。→ **export では無効**（静的化）。SSR モードでのみ Node 必須。
- **`connection()` による動的レンダリング強制**: `app/page.tsx:7` / `app/faq/page.tsx:6` で `import { connection } from "next/server"`、`if (!isStaticExportBuild()) { await connection(); }`（`app/page.tsx:14`・`:55`、`app/faq/page.tsx:13`）。→ export ビルドで**スキップ**されるため阻害しない。
- **Server Component server fetch**: `app/[slug]/page.tsx` / `app/page.tsx` が server 側で `/meta/metadata.json`・`/reports` を fetch。export では `generateStaticParams()`（`isStaticExportBuild()` 真のとき `/reports` を fetch し `status==="ready"` の slug を静的生成。SSR モードでは `[]` を返す）に倒れ、**build 時 fetch**になる。
- **shell ビルド**（`build:shell`。`NEXT_PUBLIC_OUTPUT_MODE=export` に加えて `NEXT_PUBLIC_STATIC_SHELL=1`）: `generateStaticParams()` は API を読まず、`[{ slug: "__shell__" }]` だけを返す（`app/[slug]/page.tsx:33-35`、`SHELL_SLUG` は `app/utils/static-build.ts:67`）。トップページも API を読まずに `ReportListShell` を返し、`generateMetadata()` も空を返す。レポートの本文は配布時に同梱する JSON から実行時に読む（[static-shell-export.md](./static-shell-export.md)）。したがって shell ビルドには **build 時の API 到達も要らない**。
- **middleware**: `apps/public-viewer/middleware.ts` は**存在しない**（阻害なし）。

### 2-3. 残る依存 = build 時 Node

- **OGP 動的画像**: `app/[slug]/_op-image.tsx` が `import { ImageResponse } from "next/og"`（内部に Satori/resvg wasm を Node 上で実行）。SSR モードでは `opengraph-image.tsx` 経由で **runtime に Node が必要**。
  - 🔴 **export ビルドではレポートごとの OGP 画像は生成されない**。`scripts/rename-file.mjs` が `NEXT_PUBLIC_OUTPUT_MODE=export` のとき（`:8`）`app/[slug]/opengraph-image.tsx` と `app/[slug]/opengraph-image.png`（route ディレクトリ）の**両方**（`:10`）を `_` 付きへ改名し、Next の private folder 規約でビルド対象から外すため（`build:static` が `scripts/with-renamed-files.mjs` 経由で改名し、ビルドの成否にかかわらず復元する）。通常の `build`（SSR モード）でも `:13` で `app/[slug]/opengraph-image.png/route.ts` を改名して外すので、route handler 版はどのビルドにも入らず、SSR の OGP 画像は `opengraph-image.tsx` が出す。
  - このため `app/[slug]/page.tsx` は export 時の `openGraph.images` を、`scripts/copy-image.mjs` が出力の `meta/` に置く共通画像 `/meta/ogp.png`（トップページと同じ。`getMetadataBase()` が返す metadataBase で絶対 URL に解決される）にしている。以前は生成されない `/${slug}/opengraph-image.png` を指していた。レポートごとの画像を export で出すには、route handler が placeholder の slug `-` でも prerender される（`/reports/-` の 404 でビルドが落ちる）問題と、レポート数に比例するビルド時間・API 負荷・Google Fonts 取得への対処が要る。
  - 初版のこの節は「export 用に build 時へ静的 PNG を書き出す」と記載していたが、実際の挙動は上記のとおりで、誤りだったため訂正する。

→ public-viewer は **runtime Node 依存は export で解決済**。残るのは「export ビルド自体が Node + Next + API 到達を要する」build 時依存のみ（OGP 画像はそもそも export では生成されない）。shell ビルドは API 到達も要らず、リリース時に 1 回ビルドすれば済む。

---

## 3. `apps/static-site-builder`（Express）— ⭐ 単一exe化の核心ブロッカー

| endpoint | 処理 | runtime build | 入出力 |
|---|---|---|---|
| `POST /build` (`src/index.ts:35`) | rate limit（60s/5req）後、`req.body.slugs` を `BUILD_SLUGS` に渡し **`execAsync("pnpm run build:static")` を子プロセス実行**。完了後 `archiver` で `out/` を zip 化し `application/zip`（`kouchou-ai.zip`）でストリーム返却 | **あり** | 入力 `clientDir=../../public-viewer`／出力 `clientDir/out` を zip |
| `GET /healthcheck` (`:71`) | `{status:"ok"}` | なし | なし |

- `build:static` の実体 = public-viewer `package.json` の `"build:static": "NEXT_PUBLIC_OUTPUT_MODE=export node scripts/with-renamed-files.mjs next build"`。子プロセスへ `{ ...process.env, NODE_ENV:"production", BUILD_SLUGS }` を渡す。listen `PORT=3200`。依存: `archiver` / `express` / `express-rate-limit`。
- Dockerfile も runner stage に corepack/pnpm・node_modules・public-viewer ソース一式を同梱（`CMD ["node","dist/index.js"]`）＝**runtime に Next.js ビルド環境を丸ごと必要とする**。

**事実**: ユーザーが `/build`（admin の「ダウンロード」）を叩くたびに、コンテナ内で pnpm + Next.js full build が走り `out/` を zip 配布する。public-viewer を export に寄せても **「export 静的ファイルを生成する行為」自体が runtime の Node/Next build に依存**しており、ここを runtime から外さない限り単一 exe には Node が戻ってくる。

（注: 初版で挙げた `dev` script と `src/index.ts` の不一致は解消済み。現在の `dev` は `tsx watch src/index.ts`。）

レポートのデータに依存しない shell ビルド（public-viewer の `build:shell`）と、Python 標準ライブラリだけで配布物を組み立てる `apps/api/src/services/shell_export.py`（`package_shell`）が main に入っている（手順は [static-shell-export.md](./static-shell-export.md)）。ただし admin の `/api/download` は今も上記の `/build` を中継しており、`package_shell` はまだ FastAPI のダウンロード経路につながっていない。

---

## 4. 総括 — 完了条件への含意

1. **runtime Node 依存一覧（第1項）**: 上記の通り棚卸し完了。admin は proxy + 設定、public-viewer は export 済、builder は runtime build。
2. **admin を static serve する最小方針（第2項）の素材**: §1-5 の通り、`NEXT_PUBLIC_ADMIN_API_KEY` を使う Server Action 15本の client 化 + `output:export` + API key threat model 決定でほぼ完了。
3. **static-site-builder の責務（第3項）**: ここが本丸。runtime `next build` を ① 事前ビルド済み成果物の配布、② FastAPI/Python 側での静的レポート生成、のどちらに倒すかが単一exe化の成否を決める。

次のステップは、§1-5 の admin export 化を prototype branch で実装し、`apps/admin` が Node server なしでビルド・起動できることを検証することです（完了条件の prototype 項に対応）。
