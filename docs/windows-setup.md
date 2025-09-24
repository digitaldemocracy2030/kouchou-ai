# Windows環境でのユーザーガイド

このドキュメントでは、開発者でない人がWindows環境で広聴AI（kouchou-ai）を使うための手順を説明します。
ソフトウェア開発に必要な要素を取り除いて最小限にしたものです。

## 前提条件

- Windows 10/11
- インターネット接続
- OpenAI APIキー（[取得方法](https://platform.openai.com/api-keys)）
- Gemini APIキー（[取得方法](https://ai.google.dev/gemini-api/docs/api-key)）

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
2. プロンプトが表示されたら、OpenAI APIキーとGemini APIキーを入力します（どちらか一方でも可）。
   - **注意**: Ctrl+Vでの貼り付けができない場合は、右クリックして「貼り付け」を選択してください。
3. セットアップが自動的に進行し、APIキーの有効性確認後にDockerコンテナが起動します。

### 5. アプリケーションへのアクセス

セットアップが完了すると、以下のURLでアプリケーションにアクセスできます：

- レポート閲覧画面: http://localhost:3000
- 管理画面: http://localhost:4000

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

### Docker Desktopが起動していない場合

エラーメッセージ「Docker Desktopが実行されていません」が表示された場合は、Docker Desktopを起動してから再度`setup_win.bat`を実行してください。Docker Desktopは自動起動設定をしていない限り、毎回手動で起動する必要があります。

### Dockerコマンドが認識されない場合

Dockerをインストールした直後は、コマンドのパスが通っていない場合があります。コンピューターを再起動してから再度試してください。

### APIキーの入力に関する問題

- **貼り付けができない場合**: コマンドプロンプトではCtrl+Vが機能しないことがあります。右クリックして「貼り付け」を選択するか、Alt+Spaceキーを押してから「編集」→「貼り付け」を選択してください。
**APIキーが正しく動作しない場合**: APIキーが正確にコピーされているか確認してください。OpenAI APIキーは「sk-」で始まります。Gemini APIキーは「AIza」で始まります。入力ミスがあると、後の処理でエラーが発生します。

### WSL2の有効化が必要な場合

Docker Desktopの初回起動時にWSL2の有効化を求められた場合は、指示に従ってWSL2を有効化してください。詳細は[Microsoft公式ドキュメント](https://learn.microsoft.com/ja-jp/windows/wsl/install)を参照してください。

### メモリ不足エラーが発生する場合

Docker Desktopの設定からリソース割り当て（メモリ、CPU）を増やしてください。推奨設定：

- メモリ: 4GB以上
- CPU: 2コア以上
