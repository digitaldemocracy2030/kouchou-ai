# Windows環境でのユーザーガイド

このドキュメントでは、開発者でない人がWindows環境で広聴AI（kouchou-ai）を使うための手順を説明します。
ソフトウェア開発に必要な要素を取り除いて最小限にしたものです。

## 使い方を先に選ぶ

このガイドは、Windows PC上で **Docker DesktopのLinux containersを起動できる方** 向けです。

| 状況 | 次に進む先 |
| --- | --- |
| Docker Desktopを導入・起動できる | 下の前提条件を確認して、このガイドを進める |
| 組織のPCでインストール権限・WSL2・利用条件が不明 | 所属組織のIT管理者に確認する。権限を回避して進めない |
| Docker DesktopやWSL2を利用できない | 利用可能な別環境や技術者による導入を検討する。ブラウザで動く [serverless版](https://github.com/tokoroten/kouchou-ai-serverless) も比較できる |

serverless版は別プロジェクトです。本体と同一の機能・設定・運用を保証するものではないため、必要なモデルやデータの扱いはリンク先の説明を確認してください。このガイドはWSL内の手動構築やWindows単一実行ファイルの導入手順を扱いません。

## 実行前の確認

- Windows 10/11で、Docker Desktopの対応条件を満たしている。
- インターネットへ接続でき、Docker Desktopをインストール・起動できる。
- Docker Desktopの利用条件を確認している。組織利用の場合は管理者へ確認する。
- Docker DesktopがLinux containersモードで起動している。WSL2の初期設定や再起動を求められた場合は先に完了する。
- 使用するモデルに対応する **OpenAI APIキーまたはGemini APIキーのどちらか一方** を用意する。両方を用意する必要はない。

APIキーの取得先: [OpenAI](https://platform.openai.com/api-keys) / [Gemini](https://ai.google.dev/gemini-api/docs/api-key)。キーの入力形式が正しいことと、選択モデルを実際に利用できることは別です。

## セットアップ手順

### 1. Docker Desktopのインストール

1. [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/)をダウンロードしてインストールします。
2. **インストール後、コンピューターを再起動してください**（Dockerコマンドのパスを正しく設定するために必要です）。
3. 再起動後、Docker Desktopを**明示的に起動**します（自動起動の設定をしていない場合は毎回必要です）。
4. タスクバーのDockerアイコンが実行中（緑色）になっていることを確認します。

### 2. 広聴AIのダウンロード

1. [広聴AI安定版リリース](https://github.com/digitaldemocracy2030/kouchou-ai/releases/latest)から最新の安定版をダウンロードします。
2. ダウンロードしたzipファイルを任意の場所に展開します。

### 3. APIキーの準備

1. [OpenAI API](https://platform.openai.com/api-keys)にアクセスし、OpenAI APIキーを取得します（OpenAIモデルを使用する場合）。
2. [Google AI Studio](https://ai.google.dev/gemini-api/docs/api-key)にアクセスし、Gemini APIキーを取得します（Geminiモデルを使用する場合）。
3. APIキーをコピーして、メモ帳などに一時的に保存しておくと便利です。
4. **重要**: APIキーは正確にコピーしてください。入力ミスがあると、後の処理でエラーが発生します。

### 4. セットアップの実行

1. 展開したフォルダ内の`setup_win.bat`ファイルをダブルクリックします。
2. `setup_win.ps1` の入力ダイアログが開いたら、OpenAI APIキーとGemini APIキーを入力します（どちらか一方でも可）。
   - **注意**: 入力欄でCtrl+Vの貼り付けができない場合は、右クリックして「貼り付け」を選択してください。
3. セットアップが自動的に進行し、APIキーの入力形式を確認した後にDockerコンテナが起動します。セットアップ中は実APIの接続確認を行いません。

### 5. アプリケーションへのアクセス

セットアップが完了すると、以下のURLでアプリケーションにアクセスできます：

- レポート閲覧画面: http://localhost:3000
- 管理画面: http://localhost:4000

### 起動後の確認

1. レポート閲覧画面と管理画面の両方が開くことを確認する。
2. 管理画面で、用意したAPIキーに対応するproviderとモデルを選ぶ。
3. レポート作成前の接続確認で応答を確認する。確認に失敗した場合は、表示された原因と対処を確認する。
4. まず少量の入力で作成から閲覧までを確認する。チャット接続成功だけでは埋め込みを含む全工程の完了は保証されない。

### 6. アプリケーションのアクセス・運用と再起動の手順

セットアップ後は、次回以降の起動や停止を以下のように行ってください。

#### 通常の起動・停止

- アプリケーションの起動:  
  フォルダ内の `start_win.bat` をダブルクリックします（または Docker デスクトップから操作）

- アプリケーションの停止:  
  `stop_win.bat` をダブルクリックします（または Docker デスクトップから操作）

#### APIキーを変更したい場合

OpenAI APIキーやGemini APIキーを再設定したい場合は、再度 `setup_win.bat` を実行してください。

1. 既存のアプリケーションが起動中の場合は `stop_win.bat` で停止してください。  
2. `setup_win.bat` を実行し、新しい APIキーを入力します。
3. 自動的に再ビルドと起動が行われます。

> ※ `setup_win.bat` の再実行では、既存の `.env` ファイルが上書きされます。

## トラブルシューティング

| 症状 | 確認する順番 |
| --- | --- |
| Docker Desktopを導入できない | 管理者の利用許可・端末の制約を確認し、冒頭の使い方の選択へ戻る |
| Docker Desktopが起動しない / WSL2の設定を求められる | Docker Desktopの案内に従ってWSL2設定と再起動を完了する。組織設定で禁止されている場合は管理者へ |
| Dockerコマンドが見つからない | インストール完了 → Windows再起動 → Docker Desktop起動を確認する |
| ビルドや分析がメモリ不足で止まる | Docker Desktopのリソース設定と空きメモリを確認する。入力件数を減らして再試行する |
| APIキーを貼り付けられない | 右クリックで貼り付けを試す。前後の空白・改行が入っていないか確認する |
| 画面は開くが接続確認が失敗する | provider・モデル・キー・利用可能な残高や権限を確認する。キーを変更した場合は再セットアップする |
| 画面が開かない | Docker Desktop起動 → コンテナの状態 → エラー表示を確認する |

!!! note "Windows 実機での検証を行う開発者・AI エージェント向け"
    `setup_win.bat` と Docker Desktop (Linux containers) の実機検証観点は、[Windows 実機セットアップ検証手順](../development/windows-real-machine-setup-verification.md) にまとめています。

### Docker Desktopが起動していない場合

エラーメッセージ「Docker Desktop が起動していません」が表示された場合は、Docker Desktopを起動してから再度`setup_win.bat`を実行してください。Docker Desktopは自動起動設定をしていない限り、毎回手動で起動する必要があります。

### Dockerコマンドが認識されない場合

Dockerをインストールした直後は、コマンドのパスが通っていない場合があります。コンピューターを再起動してから再度試してください。

### APIキーの入力に関する問題

- **貼り付けができない場合**: `setup_win.ps1` の入力ダイアログ内で Ctrl+V が機能しないことがあります。入力欄を右クリックして「貼り付け」を選択してください。
**APIキーが正しく動作しない場合**: APIキーが正確にコピーされているか確認してください。OpenAI APIキーは「sk-」で始まります。Gemini APIキーは「AIza」で始まります。入力ミスがあると、後の処理でエラーが発生します。

### WSL2の有効化が必要な場合

Docker Desktopの初回起動時にWSL2の有効化を求められた場合は、指示に従ってWSL2を有効化してください。詳細は[Microsoft公式ドキュメント](https://learn.microsoft.com/ja-jp/windows/wsl/install)を参照してください。

### メモリ不足エラーが発生する場合

Docker Desktopの設定からリソース割り当て（メモリ、CPU）を増やしてください。推奨設定：

- メモリ: 4GB以上
- CPU: 2コア以上
