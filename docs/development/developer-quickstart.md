# 開発者向けスタートガイド

広聴 AI の開発者向け canonical な入口ページです。**「自分はどの起動モードを使うべきか」をこのページの最初で判断**してから、対応するモードの節へ進んでください。

!!! info "一般ユーザーの方へ"
    アプリを「使う」だけが目的の方は、OS 別セットアップ（[Windows](../getting-started/windows-setup.md) / [Mac](../getting-started/mac-setup.md) / [Linux](../getting-started/linux-setup.md)）をご覧ください。本ページはローカルで広聴 AI の **コードを触る** 人向けです。

## どの起動モードを選ぶか

| やりたいこと | 推奨モード | 起動コストの目安 |
|---|---|---|
| まず動かして全体像を掴みたい / バックエンドも含めて E2E で確認したい | [Mode 1: Docker Compose](#mode-1-docker-compose) | 初回ビルド数分、以降は速い |
| public-viewer / admin の **UI だけ** を触りたい（API のロジックは触らない） | [Mode 2: dummy-server + frontend dev](#mode-2-dummy-server-frontend-dev) | pnpm + Node のみ、Docker 不要 |
| `apps/api` または `apps/admin` を **個別にデバッガで動かしたい** / ホットリロードしたい | [Mode 3: native 起動](#mode-3-native) | Rye + pnpm のローカル install |
| CSV → クラスタリング結果を CLI で回したい / `packages/analysis-core` を組み込みたい | [Mode 4: CLI / analysis-core](#mode-4-cli-analysis-core) | pip install のみ、Docker / Node 不要 |

迷ったら **Mode 1** から始めるのが安全です。Mode 1 で全体像を掴んでから、触りたいレイヤに応じて Mode 2〜4 へ降りていく流れを想定しています。

---

## Mode 1: Docker Compose（全体を一発で起動） { #mode-1-docker-compose }

### 必要なもの

- Docker Desktop または Docker Engine + Compose v2
- OpenAI / Gemini / OpenRouter / Azure OpenAI / ローカル LLM のいずれかの API キー

### 手順

```bash
git clone https://github.com/digitaldemocracy2030/kouchou-ai.git
cd kouchou-ai
cp .env.example .env
# .env を編集して OPENAI_API_KEY 等を設定
docker compose up
```

### 確認 URL

| サービス | URL |
|---|---|
| public-viewer（レポート閲覧） | <http://localhost:3000> |
| admin（レポート作成・管理） | <http://localhost:4000> |
| api（FastAPI / Swagger UI） | <http://localhost:8000/docs> |

### ローカル LLM（Ollama）を併用する場合

```bash
# .env に WITH_GPU=true を追加してから
docker compose --profile ollama up -d
```

利用するモデルは事前に `ollama pull <model>` で取得しておくと、admin UI のモデル一覧から選択できます。サポートされるモデルは [Ollama 公式モデルライブラリ](https://ollama.com/library) を参照してください。

### よくある落とし穴（Mode 1）

- **`.env` を編集したのに反映されない**: 一部の環境変数は Docker イメージのビルド時に埋め込まれます。`docker compose down && docker compose up --build` で再ビルドしてください。
- **全部起動すると遅い**: `docker compose up --no-deps public-viewer api` のように対象サービスだけ起動できます。

---

## Mode 2: dummy-server + frontend dev（UI のみ） { #mode-2-dummy-server-frontend-dev }

public-viewer / admin の UI を触りたいが、Python バックエンドは動かしたくない（または API のロジックは別途モックしたい）場合のモードです。`utils/dummy-server` が固定レスポンスを返す軽量サーバとして API を代替します。

### 必要なもの

- Node.js + **pnpm 9.15.4**（corepack 経由が推奨）。npm は非対応 ⇒ [なぜ pnpm か](why-pnpm.md)

### 手順

```bash
# 初回のみ：pnpm install と各 app の .env コピー
make client-setup

# public-viewer + admin + dummy-server を並行起動
make client-dev -j 3
```

### 確認 URL

| サービス | URL |
|---|---|
| public-viewer | <http://localhost:3000> |
| admin | <http://localhost:4000> |
| dummy-server（API モック） | <http://localhost:8000> |

### よくある落とし穴（Mode 2）

- **`pnpm` が無い**: corepack で導入してください。`corepack enable && corepack prepare pnpm@9.15.4 --activate`
- **`.env` が無いと怒られる**: `make client-setup` は `apps/public-viewer/.env-sample` / `apps/admin/.env-sample` / `utils/dummy-server/.env-sample` を `.env` にコピーします。手動で起動する場合は同じコピーを忘れずに。

---

## Mode 3: native 起動（apps/api / apps/admin を個別に） { #mode-3-native }

Python / Next.js のデバッガを使って `apps/api` や `apps/admin` を直接動かしたい場合のモードです。Docker は使いません。

### 必要なもの

- Python 3.12 + **Rye**（バックエンド）
- Node.js + pnpm 9.15.4（フロント）
- OpenAI 等の API キー

### 3-1. api を native で起動

```bash
# 1. ルートの .env（コンテナ向け）とは別に、apps/api 用の .env を用意
cp apps/api/.env.example apps/api/.env
```

`apps/api/.env` に最低限以下を入れます。

```env
ADMIN_API_KEY=admin
PUBLIC_API_KEY=public
OPENAI_API_KEY=sk-your-api-key-here
LOG_FILE=apps/api/error.log
```

```bash
cd apps/api
rye sync
rye run python -m ensurepip --upgrade
rye run python -m pip install -e ../../packages/analysis-core
make run
# -> http://localhost:8000/docs (Swagger UI)
```

!!! warning "analysis-core の editable install は必須"
    `packages/analysis-core` の editable install を忘れると、起動時に `No module named analysis_core` で落ちます。上記コマンドの 3 行目を必ず実行してください。

### 3-2. admin を native で起動

```bash
cp apps/admin/.env.example apps/admin/.env
```

`apps/admin/.env`：

```env
NEXT_PUBLIC_API_BASEPATH=http://localhost:8000
NEXT_PUBLIC_ADMIN_API_KEY=admin
NEXT_PUBLIC_CLIENT_BASEPATH=http://localhost:3000
```

```bash
cd apps/admin
pnpm dev
# -> http://localhost:4000
```

### 確認 URL

| サービス | URL |
|---|---|
| api | <http://localhost:8000/docs> |
| admin | <http://localhost:4000> |
| public-viewer（必要なら別途 `pnpm --filter @kouchou-ai/public-viewer dev`） | <http://localhost:3000> |

### よくある落とし穴（Mode 3）

- **`.env` の置き場所が複数ある**: ルートの `.env`（Docker Compose 用）/ `apps/api/.env`（native api 用）/ `apps/admin/.env`（native admin 用）は **別物** です。native モードで起動するときはルート `.env` は使われません。
- **admin のレポートリンクが `undefined`**: `apps/admin/.env` の `NEXT_PUBLIC_CLIENT_BASEPATH` が未設定です。上記のように `http://localhost:3000` を設定して `pnpm dev` を再起動してください。
- **api のエラーログ**: `LOG_FILE` 設定済みなら `apps/api/error.log` に出ます。

---

## Mode 4: CLI / analysis-core { #mode-4-cli-analysis-core }

`packages/analysis-core` を Python ライブラリ / CLI として使い、CSV → クラスタリングのパイプラインを Docker / Node なしで回すモードです。

### 必要なもの

- Python 3.12 以上
- OpenAI / Azure OpenAI / Gemini いずれかの API キー

### 手順

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install 'kouchou-ai-analysis-core[embeddings,clustering]'

kouchou-analyze --version
kouchou-analyze --config config.json --dry-run
kouchou-analyze --config config.json
```

完全なフローは [CLI クイックスタート](../user-guide/cli-quickstart.md) を参照してください（config.json の書式、出力ファイルの読み方、Azure OpenAI / Gemini 切替、トラブルシューティング含む）。

### よくある落とし穴（Mode 4）

- **`No module named analysis_core`**: base install だけだと embedding / clustering 系の依存が入りません。`pip install 'kouchou-ai-analysis-core[embeddings,clustering]'` で extras 付きで入れてください。
- **`Unknown provider: None`**: `config.json` に `"provider": "openai"` 等を明示してください。
- **`Job already running`**: 前回実行のロックです。`rm -rf outputs/<config_name>` で消してから再実行。

---

## 環境変数の置き場所まとめ

| ファイル | 使われるモード | 主な用途 |
|---|---|---|
| `.env`（ルート） | Mode 1（Docker Compose） | `docker compose` 起動時のサービス共通設定 |
| `apps/api/.env` | Mode 3（native api） | `rye run` で起動する api の設定 |
| `apps/admin/.env` | Mode 2 / Mode 3 | `pnpm dev` で起動する admin の設定 |
| `apps/public-viewer/.env` | Mode 2 / Mode 3 | `pnpm dev` で起動する public-viewer の設定 |
| `utils/dummy-server/.env` | Mode 2 | dummy-server の API キー設定 |
| `.env`（CLI 実行ディレクトリ） | Mode 4 | `kouchou-analyze` 実行時の API キー |

ルート `.env` を編集しても native / CLI モードには反映されないので、モード切替時は対象 `.env` をそれぞれ更新してください。

## 次のステップ

- API キー周りの選択肢（Azure OpenAI / Gemini / Ollama 等） ⇒ [CLI クイックスタート](../user-guide/cli-quickstart.md)
- アーキテクチャをもっと知る ⇒ [ドキュメントサイトのトップ](../index.md)
- コントリビュート手順 ⇒ [コントリビューションガイド](contributing.md)
- AI コーディングエージェント（Claude Code / Codex）と協働する ⇒ [Claude Code / Codex スキル](ai-assistants.md)
