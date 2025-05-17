
# Windows環境でのユーザーガイド（開発用にWindowsでDockerを使わずに実行する場合,非推奨）

本手順は、Windows環境で Docker を使用せずにローカル開発環境を構築するためのものです。簡易的な検証や開発用途を想定しており、本番環境や推奨構成ではありません。

## 前提条件

- Windows 10/11
- インターネット接続
- OpenAI APIキー（[取得方法](https://platform.openai.com/api-keys)）


## セットアップ手順


#### 1. リポジトリのクローン

```
git clone https://github.com/digitaldemocracy2030/kouchou-ai.git
cd kouchou-ai
```

#### 2. .env ファイルの作成

```
copy .env.example .env
```

* `.env.example` をベースに `.env` を作成し、OpenAI APIキー他、各種環境変数を設定します。

#### 3. Node.js の確認（client / client-admin用）

```
node -v
npm -v
```

* 未インストールの場合は、[Node.js LTS](https://nodejs.org/ja) をインストールしてください。

#### 4. Python の確認（server用）

```
python --version
```

* バージョンは 3.12 の使用を推奨します。  （他のバージョンでも動作する可能性はありますが、本プロジェクトでの動作確認は行っていません）
* 未インストールの場合は、[Python公式サイト](https://www.python.org/downloads/windows/) よりインストールしてください。
  
#### 5. client 側ライブラリのインストール

```
cd client
npm install
cd ..
```

#### 6. client-admin 側ライブラリのインストール

```
cd client-admin
npm install
cd ..
```

#### 7. server 側ライブラリのインストール（PDM + 仮想環境）

```
cd server
pip install pdm
pdm install
cd ..
```

#### 8. direct\_start\_win.bat を実行

* Windows用のバッチスクリプト `direct_start_win.bat` をkouchou-ai配下にコピーしダブルクリックまたはコマンドラインで実行

```
copy experimental\direct_win\direct_start_win.bat .\
direct_start_win.bat
```

#### 9. アクセス確認

* [http://localhost:3000](http://localhost:3000) : レポート一覧画面（client）
* [http://localhost:4000](http://localhost:4000) : 管理画面（client-admin）

---

> ⚠️ 注意：この構成は動作確認・検証用であり、Dockerを用いた本番環境構築を推奨します。
