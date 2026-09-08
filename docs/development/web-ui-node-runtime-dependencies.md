# Web UI の runtime Node 依存インベントリ（#885 完了条件 第1項）

current `main`（`d5c9ece`）の `apps/admin` / `apps/public-viewer` / `apps/static-site-builder` を読み、**Node.js runtime（Next.js のサーバ実行層 / Express）に依存している箇所**を網羅しました。各行は実コード根拠です。

## 結論（先に）

- **`apps/admin`**: Node runtime 依存はほぼ「FastAPI への薄い proxy」と「static export を阻害する設定」だけ。**Node 固有処理（ファイル生成 / zip / build）を行う箇所は 0**。→ client fetch + `output:"export"` 化で runtime Node をほぼ外せる（残課題は API key の threat model）。
- **`apps/public-viewer`**: 既に `NEXT_PUBLIC_OUTPUT_MODE=export` モードを持ち、**runtime の Node 依存（ISR / `connection()` / server fetch）は export ビルドで build 時処理に倒れて解決済**。残るのは「export ビルドそのものに Node + Next + API 到達が必要」という **build 時依存**。
- **`apps/static-site-builder`**: ⭐ **単一exe化の最大の障壁**。`/build` を叩くたびに **runtime で `next build`（`pnpm run build:static`）を子プロセス実行**して `out/` を zip 返却する設計。「静的ファイルを生成する行為そのもの」が runtime の Node/Next build に依存している。

つまり #885 で本当に解くべきは admin の proxy 置換（容易）ではなく、**static-site-builder の runtime build をどう runtime から外すか**（事前ビルド成果物の配布 or Python 側での静的レポート生成）です。

---

## 1. `apps/admin`（Next.js 管理画面）

### 1-1. Server Actions（計 15・全て FastAPI proxy）

| ファイル | action | 内容 | 除去難易度 |
|---|---|---|---|
| `_components/ReportCard/ClusterEditDialog/actions.ts` | `fetchClusters`, `updateCluster` | `/admin/reports/{slug}/cluster-labels` GET, `/cluster-label` PATCH の proxy | 低 |
| `_components/ReportCard/DeleteDialog/action.ts` | `reportDelete` | `/admin/reports/{slug}` DELETE proxy | 低 |
| `_components/ReportCard/DuplicateReportDialog/actions.ts` | `duplicateReport` | `/admin/reports/{slug}/duplicate` POST。**`process.env.ADMIN_API_KEY`（非PUBLIC）使用** | 中（key 露出判断） |
| `_components/ReportCard/ReportEditDialog/actions.ts` | `updateReportConfig` | `/admin/reports/{slug}/config` PATCH proxy | 低 |
| `_components/ReportCard/Visibility/actions.ts` | `updateReportVisibility` | `/admin/reports/{slug}/visibility` PATCH proxy | 低 |
| `_components/ReportCard/VisualizationConfigDialog/actions.ts` | `fetchVisualizationConfig`, `updateVisualizationConfig` | `/admin/reports/{slug}/visualization-config` GET/PATCH proxy | 低 |
| `create/api/createReport.ts` | `createReport` | `/admin/reports` POST（コメント全件 body）。`serverActions.bodySizeLimit:"100mb"` 前提 | 中（大容量 POST + CORS） |
| `create/api/plugins.ts` | `getPlugins`, `validatePluginSource`, `previewPluginData`, `importPluginData` | `/admin/plugins` 系 GET/POST 4本 proxy | 低 |
| `create/components/EnvironmentCheckDialog/verifyApiKey.ts` | `verifyApiKey`, `verifyChatGptApiKeyWithProvider` | `/admin/environment/verify`, `/verify-chatgpt` GET proxy | 低 |

すべて `getApiBaseUrl()` + `x-api-key` で内部 API を中継するだけ。サーバ専用シークレットを使うのは `duplicateReport`（`ADMIN_API_KEY`）のみ、他は `NEXT_PUBLIC_ADMIN_API_KEY`（client 露出可）。

### 1-2. Route Handlers（3本）

| route | 役割 | 種別 | 使用 env |
|---|---|---|---|
| `app/api/download/route.ts` (POST) | body の `slugs` を `${CLIENT_STATIC_BUILD_BASEPATH}/build` に POST し、返ってきた zip ストリームを `Content-Disposition: attachment; filename=kouchou-ai-<JST>.zip` で中継 | ストリーム中継 + ファイル名生成 | `CLIENT_STATIC_BUILD_BASEPATH` |
| `app/api/admin/reports/[slug]/config/route.ts` (GET) | `/admin/reports/{slug}/config` 中継。**`ADMIN_API_KEY` をブラウザに出さないための proxy 層**。`reuse/[slug]/page.tsx` の client fetch が経由 | proxy | `ADMIN_API_KEY`, `API_BASEPATH ?? NEXT_PUBLIC_API_BASEPATH` |
| `app/api/healthcheck/route.ts` (GET) | `{status:"ok"}` を返すだけ。middleware の Basic 認証を bypass する対象 | 静的応答 | なし |

### 1-3. Server-side data fetch（static export 阻害）

- `app/page.tsx`: **Server Component で `fetch(${apiUrl}/admin/reports, { cache:"no-store" })`** を server 実行（`x-api-key` 付与）。`no-store` ＝ 完全動的レンダリングで `output:"export"` を直接阻害。**admin で server fetch しているのはここ 1本のみ**。
- `reuse/[slug]/page.tsx` / `create/page.tsx` は `"use client"`（初期 server fetch なし）。`layout.tsx` は server fetch なし（`process.env` を build/SSR 参照のみ）。

### 1-4. middleware / next.config / instrumentation

- **`middleware.ts`**: Basic 認証（`BASIC_AUTH_USERNAME` / `PASSWORD` 両設定時のみ有効、`Buffer.from(...,"base64")` でデコード比較、失敗時 401）。`/api/healthcheck` は無条件 bypass。→ middleware は `output:"export"` で**使用不可**（Next がエラー）。
- **`next.config.ts`**: `output:"standalone"`（**export ではない＝最大の阻害設定**）。`async headers()` で全パスに CSP 付与（実体は `apps/shared/csp.ts` の `buildCspHeaderValue()`：`default-src 'self'` 基調、GA 有効時に googletagmanager 等を追加）。`serverActions.bodySizeLimit:"100mb"`。
- **`instrumentation.server.ts`**: `node:fs`（`readFileSync`/`existsSync`）+ `node:path` を直 import し、起動時に `.env` の override 診断を `console.warn`（機能本体ではなく開発支援）。`instrumentation.ts` は `NEXT_RUNTIME==="nodejs"` ガード付き。

### 1-5. admin の除去難易度マップ

| 依存 | 難易度 | 方針 |
|---|---|---|
| Server Action 14本（proxy） | 低 | 両モードで動く client API モジュールへ置換 |
| `duplicateReport` / `config` route（`ADMIN_API_KEY`） | 中 | local desktop の threat model で client 露出許容 or FastAPI 直 |
| `healthcheck` route | 低 | export で不要化 |
| `page.tsx` server fetch | 中 | client fetch + loading 化 |
| `download` route（zip 中継） | 中 | static-site-builder を直接叩く / FastAPI 移管（§3 と連動） |
| `output:standalone` / CSP / Basic 認証 / instrumentation `node:fs` | 設定 | export 化、CSP は静的ホスト or Python 側、Basic 認証は local 不要、instrumentation は export 時除外可 |

---

## 2. `apps/public-viewer`（Next.js 公開レポート閲覧）

既に `NEXT_PUBLIC_OUTPUT_MODE === "export"` トグル（`next.config.ts`）と `app/utils/static-build.ts` の `isStaticExportBuild()` を持ち、**export 阻害要因はフラグ分岐で無効化済み**。

### 2-1. Route Handlers

| route | 役割 | 種別 | 使用 env |
|---|---|---|---|
| `app/api/revalidate/route.ts` (POST) | `{tag, secret}` を検証し `revalidateTag(tag,"max")` | **Node固有（ISR）**。`output:"export"` 下では成立しない | `REVALIDATE_SECRET` |
| `app/[slug]/opengraph-image.png/route.ts` (GET) | export 時の OGP 画像生成 route。`_op-image.tsx` の `OpImage(slug)` を呼ぶ | **Node固有（`next/og`）**。後述の通り build 時生成 | `NEXT_PUBLIC_PUBLIC_API_KEY` 経由 |

### 2-2. runtime Node 依存 → export で解決済（SSR モード専用に残存）

- **ISR / revalidate**: `app/[slug]/page.tsx:25` `export const revalidate = 300`、`app/page.tsx:13` 同。`fetch(..., { next:{ tags:["meta"] } })` 等のタグ付きキャッシュ + `api/revalidate` の `revalidateTag` がペア。→ **export では無効**（静的化）。SSR モードでのみ Node 必須。
- **`connection()` による動的レンダリング強制**: `app/page.tsx:9` / `app/faq/page.tsx:6` で `import { connection } from "next/server"`、`if (!isStaticExportBuild()) { await connection(); }`。→ export ビルドで**スキップ**されるため阻害しない。
- **Server Component server fetch**: `app/[slug]/page.tsx` / `app/page.tsx` が server 側で `/meta/metadata.json`・`/reports` を fetch。export では `generateStaticParams()`（`isStaticExportBuild()` 真のとき `/reports` を fetch し `status==="ready"` の slug を静的生成）に倒れ、**build 時 fetch**になる。
- **middleware**: `apps/public-viewer/middleware.ts` は**存在しない**（阻害なし）。

### 2-3. 残る依存 = build 時 Node

- **OGP 動的画像**: `app/[slug]/_op-image.tsx` が `import { ImageResponse } from "next/og"`（内部に Satori/resvg wasm を Node 上で実行）。export 用に `opengraph-image.png/route.ts` で**ビルド時に静的 PNG 書き出し**（runtime には残らないが **`next build` に Node 必須**）。ビルド時に Google Fonts へ外部 fetch + API へ `fetchApiWithRetry(/reports/${slug})` も発生＝**ビルドにネットワーク到達が必要**。

→ public-viewer は **runtime Node 依存は export で解決済**。残るのは「export ビルド自体が Node + Next + API 到達を要する」build 時依存のみ。

---

## 3. `apps/static-site-builder`（Express）— ⭐ 単一exe化の核心ブロッカー

| endpoint | 処理 | runtime build | 入出力 |
|---|---|---|---|
| `POST /build` (`src/index.ts:35`) | rate limit（60s/5req）後、`req.body.slugs` を `BUILD_SLUGS` に渡し **`execAsync("pnpm run build:static")` を子プロセス実行**。完了後 `archiver` で `out/` を zip 化し `application/zip`（`kouchou-ai.zip`）でストリーム返却 | **あり** | 入力 `clientDir=../../public-viewer`／出力 `clientDir/out` を zip |
| `GET /healthcheck` (`:78`) | `{status:"ok"}` | なし | なし |

- `build:static` の実体 = public-viewer `package.json` の `"build:static": "NEXT_PUBLIC_OUTPUT_MODE=export next build"`。子プロセスへ `{ ...process.env, NODE_ENV:"production", BUILD_SLUGS }` を渡す。listen `PORT=3200`。依存: `archiver` / `express` / `express-rate-limit`。
- Dockerfile も runner stage に corepack/pnpm・node_modules・public-viewer ソース一式を同梱（`CMD ["node","dist/index.js"]`）＝**runtime に Next.js ビルド環境を丸ごと必要とする**。

**事実**: ユーザーが `/build`（admin の「ダウンロード」）を叩くたびに、コンテナ内で pnpm + Next.js full build が走り `out/` を zip 配布する。public-viewer を export に寄せても **「export 静的ファイルを生成する行為」自体が runtime の Node/Next build に依存**しており、ここを runtime から外さない限り単一 exe には Node が戻ってくる。

（注: `package.json` の `dev` script が参照する `src/server.ts` は実在せず、実体は `src/index.ts` のみ＝dev script と不一致。別件の軽微な掃除候補。）

---

## 4. 総括 — 完了条件への含意

1. **runtime Node 依存一覧（第1項）**: 上記の通り棚卸し完了。admin は proxy + 設定、public-viewer は export 済、builder は runtime build。
2. **admin を static serve する最小方針（第2項）の素材**: §1-5 の通り、proxy 14本の client 化 + `output:export` + API key threat model 決定でほぼ完了。
3. **static-site-builder の責務（第3項）**: ここが本丸。runtime `next build` を ① 事前ビルド済み成果物の配布、② FastAPI/Python 側での静的レポート生成、のどちらに倒すかが単一exe化の成否を決める。

次のステップは、§1-5 の admin export 化を prototype branch で実装し、`apps/admin` が Node server なしでビルド・起動できることを検証することです（完了条件の prototype 項に対応）。
