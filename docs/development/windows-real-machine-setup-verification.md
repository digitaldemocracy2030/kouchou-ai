# Windows 実機セットアップ検証手順

このページは、Windows 実機または Windows self-hosted runner 上で `setup_win.bat` と Docker Desktop（Linux containers）を使ったセットアップを検証するための手順です。

`windows-latest` hosted runner では Docker Desktop + Linux containers の実セットアップを完全には再現しにくいため、この手順は人間または AI エージェントが実機で再実行し、観測結果を Issue / PR に残すためのものです。

## 対象

- Windows 10 / 11 の実機
- Docker Desktop for Windows
- Docker Desktop の Linux containers モード
- 配布 zip を展開して `setup_win.bat` を実行する導線

## 非対象

- GitHub Actions の `windows-latest` hosted runner だけで Docker Desktop + Linux containers の実セットアップを完結させること
- WSL 内で `setup_linux.sh` を実行する導線
- Windows ネイティブ環境で個別サービスを手動起動する開発者向け導線

## テスト層の分け方

Windows セットアップ検証は、重さと再現できる範囲が異なるため、次の 3 層に分けます。

| 層 | 目的 | 実行環境 | 頻度 |
| --- | --- | --- | --- |
| Script test | 文字化け、構文、`.env` 生成、入力分岐を検出する | GitHub hosted `windows-latest` | 全 PR |
| Compose smoke | `docker compose up` で主要サービスが起動することを確認する | Linux runner でも可 | 全 PR または main |
| Real Windows E2E | Windows + Docker Desktop + `setup_win.bat` の実導線を確認する | self-hosted Windows runner / 実機 | nightly / release 前 |

このページは主に Real Windows E2E の観測手順を扱います。あわせて、`setup_win.bat` の明らかな壊れ方は `windows-latest` 上の Script test で早めに検出します。

## 事前準備

1. Windows Update を適用し、必要なら再起動します。
2. Docker Desktop for Windows をインストールします。
3. Docker Desktop の初回起動時に WSL2 の有効化を求められた場合は、案内に従って有効化します。
4. Docker Desktop のインストール直後は Windows を再起動します。
5. Docker Desktop を起動し、Linux containers モードで動いていることを確認します。
6. OpenAI API キーまたは Gemini API キーを用意します。どちらか一方だけでも構いません。
7. kouchou-ai のリリース zip または検証対象ブランチの zip を、空白や日本語を含まない短いパスに展開します。

例:

```text
C:\kouchou-ai-test\kouchou-ai
```

## Docker Desktop の確認

PowerShell またはコマンドプロンプトで、展開したフォルダに移動する前に以下を確認します。

```powershell
docker --version
docker compose version
docker info
```

確認観点:

- `docker info` がエラーにならない
- Docker Desktop が Linux containers モードになっている
- Docker Desktop の Resources で、少なくとも CPU 2 core / Memory 4 GB 程度を割り当てている

## `setup_win.bat` の実行

1. 展開したフォルダを開きます。
2. `setup_win.bat` をダブルクリックします。
3. Docker Desktop 未起動エラーが出た場合は、Docker Desktop を起動してから再実行します。
4. OpenAI API キーと Gemini API キーを入力します。不要な方は空欄で Enter を押します。
5. API キー形式の警告が出た場合は、入力ミスでないか確認します。
6. `docker compose up -d --build` が開始されることを確認します。

確認観点:

- バッチ実行中に文字化けした行がコマンドとして実行されない
- API キー入力の案内が読める
- 空欄の API キーが許容される
- 不正な形式の API キーでは警告が表示され、続行するか選べる
- `.env` が生成される
- `docker compose up -d --build` が実行される

## CI / AI エージェント向け非対話モード

CI や AI エージェントが `setup_win.bat` を確認する場合は、対話入力の代わりに非対話モードを使えます。

```bat
setup_win.bat --non-interactive --skip-docker-start --openai-api-key sk-test --gemini-api-key AIza-test
```

利用できるオプション:

| オプション | 用途 |
| --- | --- |
| `--non-interactive` | `set /p`, `choice`, `pause` を避け、CI で止まらないようにする |
| `--skip-docker-start` | Docker Desktop の確認と `docker compose up -d --build` をスキップし、`.env` 生成までを見る |
| `--skip-api-key-validation` | API キー形式チェックをスキップする |
| `--openai-api-key <value>` | OpenAI API キーを引数で渡す |
| `--gemini-api-key <value>` | Gemini API キーを引数で渡す |

GitHub hosted `windows-latest` では Docker Desktop + Linux containers の実セットアップまでは見ません。代わりに、次のような軽量チェックを行います。

- `setup_win.bat` が ASCII / UTF-8 として読める
- Docker 未起動時に期待したエラーで終了する
- 非対話モードで `.env` が生成される
- 出力に mojibake replacement character が混じらない

Self-hosted runner はローカル実機の Docker Desktop と workspace を使うため、任意の PR で走らせないでください。PR 起動時の Real Windows E2E は、PR author が `nishio` の場合だけ実行します。nightly schedule と手動 `workflow_dispatch` は維持します。

## 起動確認

セットアップ完了後、以下にアクセスします。

| 画面 | URL | 確認内容 |
| --- | --- | --- |
| レポート閲覧画面 | <http://localhost:3000> | ページが表示される |
| 管理画面 | <http://localhost:4000> | ページが表示される |
| API | <http://localhost:8000/docs> | FastAPI docs が表示される |

追加で以下を確認します。

```powershell
docker compose ps
docker compose logs --tail=100 api
docker compose logs --tail=100 admin
docker compose logs --tail=100 public-viewer
```

確認観点:

- `api`, `admin`, `public-viewer` が起動している
- `api` の build が PyTorch / dependency install で失敗していない
- ブラウザで管理画面と閲覧画面を開ける
- `.env` の `NEXT_PUBLIC_API_BASEPATH` / `NEXT_PUBLIC_CLIENT_BASEPATH` が localhost の既定値になっている

## 最小操作確認

可能であれば、管理画面で以下を確認します。

1. 管理画面を開く
2. 新規レポート作成画面に進む
3. 小さな CSV をアップロードする
4. レポート ID を入力する
5. 設定画面まで進めることを確認する

実 API キーを使った LLM 呼び出しまで行うかは、検証目的と費用に応じて判断します。API キーを使わない UI 導線の確認だけでも、Windows セットアップ検証として価値があります。

## 停止と再実行

検証後は以下で停止します。

```powershell
docker compose down
```

再実行確認をする場合は、以下を見ます。

- `setup_win.bat` の再実行で既存 `.env` が上書きされる
- API キーを変更して `.env` に反映される
- `docker compose up -d --build` が再実行される

## エラー時に残す情報

Issue / PR コメントには、個人情報や API キーを含めず、以下を残します。

- Windows のバージョン
- Docker Desktop のバージョン
- Docker Desktop が Linux containers モードかどうか
- 検証したブランチまたはリリースバージョン
- `docker compose ps` の結果
- 失敗したコマンド
- エラーログの該当部分
- 画面 URL の到達可否

API キー、ローカルユーザー名、メールアドレス、端末固有の絶対パスは貼らないでください。ログに含まれる場合は伏せ字にします。

## AI エージェント向け観測ポイント

AI エージェントが実機または self-hosted runner で検証する場合は、以下を短く報告します。

- `setup_win.bat` がどこまで進んだか
- Docker Desktop 未起動時のエラー表示が読めるか
- API キー入力と形式警告が期待通りか
- `.env` が期待通り生成されたか
- `docker compose up -d --build` の成否
- `localhost:3000`, `localhost:4000`, `localhost:8000/docs` の到達可否
- 失敗した場合、最初に失敗したコマンドとログ

成功時の報告例:

```text
Windows 11 + Docker Desktop Linux containers で setup_win.bat を実行。
.env 生成、docker compose build / up、localhost:3000, 4000, 8000/docs の表示まで確認。
API キー値やローカルユーザー名はログから除外済み。
```

失敗時の報告例:

```text
setup_win.bat は API キー入力後に docker compose build まで到達。
api image build 中に dependency install で失敗。
docker compose logs --tail=100 api の該当エラーを添付。API キーとローカルパスは伏せ字化済み。
```
