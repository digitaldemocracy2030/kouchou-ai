# レポート作成画面の「APIキー」欄に入力したキーが結果ファイルに書き出されていた問題（v4.2.0 で修正）

v4.1.0 など 2026-05-29 以降の広聴AI で、レポート作成画面の任意の「APIキー」欄に入力したキーが、レポートの結果ファイルに平文で書き出されていました。v4.2.0（2026-10-26）で修正しています。

このページでは、影響を受ける条件と、既存のレポートの確認・対処の手順を説明します。

!!! note "まず確認してください：影響を受けるのは「APIキー」欄に入力した場合だけです"
    このページでいう「ユーザー API キー」は、管理画面のレポート作成画面で「レポート生成設定」を開くと表示される、**任意の「APIキー」欄**（「独自のAPIキーを入力（空欄の場合はサーバー設定を使用）」）に入力したキーのことです。

    - この欄は既定では閉じていて、空欄のままならサーバーに設定したキーで分析します。AI プロバイダが OpenAI・Gemini・OpenRouter のときだけ表示されます（Azure・ローカル LLM では表示されません）。
    - **この欄を空のまま使っていた場合は、影響を受けません。** サーバーの `.env` や環境変数に設定したキー（`OPENAI_API_KEY`・`GEMINI_API_KEY`・`OPENROUTER_API_KEY`・Azure の設定など）は、結果ファイルに書き出されていません。
    - CLI の場合は、環境変数 `USER_API_KEY` を設定して実行したときだけが対象です（[影響を受ける条件](#conditions)）。

!!! warning "該当する場合にすること"
    1. 入力したキーを**無効化して、新しいキーを発行**する（[利用者の方](#key-owners)）
    2. 既存のレポートからキーを**取り除く**（[運用者の方](#operators)）
    3. **v4.2.0 以降に更新**する（CLI は PyPI の `kouchou-ai-analysis-core` 0.2.0 以降）

## 何が起きていたか

管理画面のレポート作成画面の「APIキー」欄（独自の OpenAI / Gemini / OpenRouter のキーを入力する欄）にキーを入力すると、そのキーがレポートの結果ファイル `hierarchical_result.json` の `config.user_api_key` に**平文で書き出されて**いました。

公開ビューアはこのファイルをそのまま読み込むため、キーは次の場所に含まれていました。

- 公開ビューアのレポートページ（ページの HTML に埋め込まれる）
- 公開 API `/reports/{slug}`
- 管理画面の「HTML書き出し」「全レポートをエクスポート」で作る静的書き出し（ZIP）と、それを置いた公開サイト
- ストレージ（Azure Blob Storage など）に同期したファイル
- 管理画面の「JSONダウンロード」で保存したファイル

また、抽出・意見分類の実行中は、処理の状態を記録するファイル `hierarchical_status.json` にもキーが書かれていました。処理が途中で異常終了する（強制終了・メモリ不足など）と、そのまま残ります。このファイルは公開 API では返りませんが、サーバーとストレージ上には残ります。

サーバーの環境変数に設定したキー（`OPENAI_API_KEY` など）は書き出されません。対象は、「APIキー」欄などでレポートごとに渡したキーだけです。

## 影響を受ける条件 { #conditions }

**2026-05-29 以降の版**（v4.1.0、PyPI の `kouchou-ai-analysis-core` 0.1.3 を含む）で、次のいずれかに当たる場合です。

- 管理画面の「APIキー」欄にキーを入力して、レポートを**作成**した
- API に直接、キー（`x-user-api-key` ヘッダー）を付けてレポートの**複製**を要求した
- CLI（`kouchou-analyze`）を、環境変数 `USER_API_KEY` を設定して実行した

次の操作では、キーは新たに書き込まれません。

- 管理画面の再利用ページからの複製（修正前の管理画面は、複製のときにキーを送っていませんでした）
- レポートの編集（タイトル・意見グループ名など）

公開範囲が「公開」または「限定公開」のレポートは、ページを閲覧できる第三者にキーを見られた可能性があります。「非公開」のレポートは公開ビューアからは見えませんが、サーバーとストレージ上のファイルにはキーが残っているので、同じように対処してください。

原因は PR [#868](https://github.com/digitaldemocracy2030/kouchou-ai/pull/868)（2026-05-29 merge）で入りました。それより前の版（v4.0.0 以前、`kouchou-ai-analysis-core` 0.1.2 以前）は該当しません。

## 確認方法

確認用のスクリプト `check_report_secret_leak.py` を使います。

- 置き場所：リポジトリの [`apps/api/scripts/`](https://github.com/digitaldemocracy2030/kouchou-ai/tree/main/apps/api/scripts)（v4.2.0 以降。API の Docker イメージでは `/app/scripts/`）。リポジトリを手元に置いていない場合は、このファイルだけをダウンロードして使えます。
- Python 3.10 以上があれば、追加のインストールなしで動きます。
- 指定した URL やファイルを読むだけで、どこかへ送信することはありません。見つかったキーも、先頭と末尾の 4 文字と長さしか表示しません。

### 公開ページの URL を指定する

公開ビューアのレポートページの URL を指定します。API キーは要りません。レポートを公開している人でも、閲覧した人でも確認できます。

```bash
python check_report_secret_leak.py https://<公開ビューア>/<レポートのslug>
```

URL は複数並べて指定できます。

### 運用者：公開中のレポートを全件確認する

公開 API のベース URL と、公開 API のキー（`PUBLIC_API_KEY`）を指定して、`--all` を付けます。

```bash
python check_report_secret_leak.py --api-base https://<API> --api-key <PUBLIC_API_KEY> --all
```

`--all` が確認するのは、公開 API の一覧に出るレポート（作成が完了し、公開範囲が「公開」または「限定公開」のもの）です。「非公開」のレポートと `hierarchical_status.json` は、次のファイルを直接確認する方法で確かめてください。

### 運用者：サーバー上のファイルを直接確認する

レポートの出力ディレクトリ（`<出力ディレクトリ>/<slug>/` が並んでいる場所）を `--report-dir` で指定します。非公開のレポートも含め、`hierarchical_result.json` と `hierarchical_status.json` の両方を確認します。

```bash
python check_report_secret_leak.py --report-dir <レポートの出力ディレクトリ>
```

Docker Compose で動かしている場合は、API のコンテナの中で実行できます。

```bash
docker compose exec api python scripts/check_report_secret_leak.py --report-dir broadlistening/pipeline/outputs
```

### CLI で作ったレポートを確認する

CLI の出力先（既定では `outputs`）を `--report-dir` で指定します。

```bash
python check_report_secret_leak.py --report-dir outputs
```

CLI が出力する `report.html` にも、結果ファイルの内容が埋め込まれています。`report.html` はこのスクリプトでは確認できないので、文字列 `user_api_key` が含まれていないかを確かめてください。

```bash
grep -l user_api_key outputs/*/report.html
```

ファイル名が表示されたら、その `report.html` にはキーが含まれています。

### 結果の読み方

`[LEAK]` と表示されたものは対処が必要です。

```text
[OK]    reports/clean-report/hierarchical_result.json
[LEAK]  reports/leaky-report/hierarchical_result.json
          $.config.user_api_key = sk-p…wxyz (len=38)
[OK]    reports/clean-report/hierarchical_status.json
[LEAK]  reports/leaky-report/hierarchical_status.json
          $.user_api_key = sk-p…wxyz (len=38)
[LEAK]  reports/stuck-report/hierarchical_status.json
          $.user_api_key = sk-p…wxyz (len=38)

確認 5 件 / 漏洩あり 3 件 / エラー 0 件
```

| 終了コード | 意味 |
|---|---|
| 0 | キーは見つからなかった |
| 1 | キーが 1 件以上見つかった（`[LEAK]`） |
| 2 | キーは見つからなかったが、読めなかった対象がある（`[ERROR]`。URL の誤り、404、ファイルが JSON でない など） |

`--show-internal-paths` を付けると、結果ファイルに残っているサーバー内部のパス（`_output_base_dir` など）も表示します。これらも次の修正スクリプトで取り除かれます。

## 対処方法

### レポートを公開している運用者の方 { #operators }

1. **v4.2.0 以降に更新する。** 更新しないと、今後作るレポートに再びキーが書き込まれます。
2. **既存のレポートを修正する。** 修正用のスクリプト `scrub_report_secrets.py`（`check_report_secret_leak.py` と同じ場所にあります）を使います。

    - レポートの中身（意見・クラスタ・ラベル・概要）には触れません。`hierarchical_result.json` の `config` からキーとサーバー内部のパスだけを、`hierarchical_status.json` からキーだけを取り除きます。
    - レポートの再生成や、LLM の再実行はしません。
    - API の設定を読むので、API のコンテナの中の、`src/` があるディレクトリ（Docker イメージでは `/app`、リポジトリでは `apps/api`）で実行します。`--report-dir` を省略すると、API の設定のレポート出力ディレクトリが対象になります。

    まず、確認だけを行います（ファイルは変更しません）。

    ```bash
    docker compose exec api python scripts/scrub_report_secrets.py
    ```

    ```text
    [OK]    clean-report
    [LEAK ] leaky-report: config.user_api_key, config._output_base_dir, config._input_base_dir
    [OK]    clean-report/hierarchical_status.json
    [LEAK ] leaky-report/hierarchical_status.json: $.user_api_key
    [LEAK ] stuck-report/hierarchical_status.json: $.user_api_key

    確認のみ（--apply で修正）: 対象 5 件 / 要修正 3 件 / エラー 0 件
    ```

    `[LEAK ]` はキーを含むもの、`[PATH ]` はサーバー内部のパスだけを含むものです。次に `--apply` を付けて修正します。

    ```bash
    docker compose exec api python scripts/scrub_report_secrets.py \
      --apply --backup-dir <レポートの出力ディレクトリの外の安全な場所> \
      --sync-storage --revalidate
    ```

    ```text
    [LEAK ] leaky-report: config.user_api_key, config._output_base_dir, config._input_base_dir
              -> 修正済み
              -> ストレージへ反映: outputs/leaky-report/hierarchical_result.json
              -> キャッシュを破棄（公開ビューアの URL を check_report_secret_leak.py で確認してください）
    ...
    修正: 対象 5 件 / 要修正 3 件 / エラー 0 件
    元ファイルの退避先: <退避先>/<日時>（API キーを含むため、確認後に安全に削除してください）
    ```

    - `--backup-dir`：修正前のファイルの退避先です。レポートの出力ディレクトリの中は指定できません（ストレージ同期の対象になるため）。退避したファイルにはキーが含まれるので、確認が済んだら安全に削除してください。`docker compose exec` で実行する場合は、コンテナの中のパスを指定します。退避しない場合は、代わりに `--no-backup` を指定します。
    - `--sync-storage`：修正後のファイルをストレージ（Azure Blob Storage など）に上書きします。ストレージを使う構成では**必ず付けてください**。付けないと、再起動時に修正前のファイルがストレージからダウンロードされて元に戻ります。
    - `--revalidate`：公開ビューアのキャッシュを破棄します。破棄に失敗したレポートは `[ERROR] <slug>: キャッシュ破棄に失敗（ファイルは修正済み）` と表示され、終了コードが 1 になります。ファイルは修正済みなので、再実行しても対象になりません。API の環境変数 `REVALIDATE_URL` / `REVALIDATE_SECRET` を確かめてください。
    - `--slug <slug>` で対象のレポートを絞れます（複数指定可）。
    - 終了コードは、エラーが無ければ 0、`[ERROR]` があれば 1 です。確認だけのときは、`[LEAK ]` があっても 0 になります。

3. **公開ページを確認する。** 修正後に、公開ビューアのレポートページを `check_report_secret_leak.py` で確認し、`[OK]` になることを確かめてください。古い版の公開ビューアは、キャッシュ破棄の後の最初のアクセスで、まだ古いページを返すことがあります。一度ページを開いてから確認してください。
4. **静的書き出しを作り直す。** 書き出し済みの ZIP や、それを置いた公開サイト、「JSONダウンロード」で保存したファイルは、スクリプトでは直せません。修正後に書き出し直して、差し替えてください。
5. **キーを入力した利用者に連絡する。** `[LEAK]` になったレポートの作成者に、下の「[キーを入力した利用者の方](#key-owners)」の対応を依頼してください。

### CLI でレポートを作った方

1. `kouchou-ai-analysis-core` を 0.2.0 以降に更新します。

    ```bash
    pip install -U 'kouchou-ai-analysis-core>=0.2.0'
    ```

2. 出力先のファイルからキーを取り除きます。`scrub_report_secrets.py` は、`--report-dir` を指定すれば API が無くても動きます（`--sync-storage` / `--revalidate` は使いません）。

    ```bash
    python scrub_report_secrets.py --report-dir outputs                                      # 確認だけ
    python scrub_report_secrets.py --report-dir outputs --apply --backup-dir <outputs の外の場所>
    ```

3. `report.html` を作り直します。修正後の結果ファイルから HTML を作るだけで、LLM の再実行や API キーは要りません。

    ```bash
    kouchou-analyze --config <設定ファイル>.json --only hierarchical_visualization --force
    ```

4. `check_report_secret_leak.py --report-dir outputs` と `grep -l user_api_key outputs/*/report.html` で、キーが残っていないことを確かめます。すでに共有した `report.html` や結果ファイルがあれば、差し替えてください。

### キーを入力した利用者の方 { #key-owners }

**キーを無効化して、新しいキーを発行してください。** 運用者がファイルを修正しても、すでに第三者に見られた可能性は消せないためです。

- OpenAI：<https://platform.openai.com/api-keys>
- Azure OpenAI：Azure Portal の対象リソース →「キーとエンドポイント」→ キーを再生成
- Google Gemini：<https://aistudio.google.com/apikey>
- OpenRouter：<https://openrouter.ai/settings/keys>

あわせて、各サービスの利用履歴・請求に心当たりのない利用がないかを確認してください。

### 更新できない場合

v4.2.0 に更新するまでは、レポート作成画面の「APIキー」欄を使わず、サーバーの環境変数でキーを設定してください。

## GitHub Pages で公開している場合

静的書き出しを GitHub の公開リポジトリに置いて GitHub Pages で公開している場合は、多くのケースで GitHub 側の仕組みがすでに働いているはずです。

- GitHub は公開リポジトリに push された内容を自動でスキャンしています（[secret scanning](https://docs.github.com/en/code-security/reference/secret-security/supported-secret-scanning-patterns)）。OpenAI・OpenRouter・Azure OpenAI・Google の API キーは「パートナー」対象で、見つかるとキーの発行元に通知され、発行元がキーを無効化してキーの持ち主に連絡します（[OpenAI の例](https://github.blog/changelog/2021-06-08-rubygems-adobe-and-openai-are-now-github-secret-scanning-integrators)）。
- push の時点でキーを検出して止める仕組み（push protection）もあります。

そのため、キーが入った書き出しを GitHub に push していても、すでにキーが無効化されている可能性が高いと考えられます。ただし、次の点は残ります。

- 対象になるのは GitHub に push されたファイルだけです。自前のサーバーやクラウドで動かしている公開ビューア、Actions の中でビルドしてリポジトリに残らない形の公開、GitHub 以外の場所に置いた ZIP は対象外です。
- 無効化するかどうかは発行元の判断で、連絡が行くのはキーの持ち主（キーを入力した利用者）です。レポートを公開した人には知らされないことがあります。
- キーの形式によっては検出されないことがあります（例：Gemini 専用の形式は、GitHub の一覧ではパートナー対象外になっています）。
- キーが無効化されても、リポジトリの履歴にはキーが残ります。

安心材料として受け取りつつ、上の確認と対処は一度行ってください。

## 修正の内容と版

- 修正：PR [#1136](https://github.com/digitaldemocracy2030/kouchou-ai/pull/1136)（2026-10-26 merge）。結果ファイルと状態ファイルに書き出す直前に、非公開のキー（ユーザー API キー、サーバー内部のパス、スタックトレース）を取り除きます。確認・修正のスクリプトも、この PR で入りました。
- 修正を含む版：[v4.2.0](https://github.com/digitaldemocracy2030/kouchou-ai/releases/tag/v4.2.0)（2026-10-26）、PyPI の [`kouchou-ai-analysis-core` 0.2.0](https://pypi.org/project/kouchou-ai-analysis-core/0.2.0/)

| 日付 | 内容 |
|---|---|
| 2026-05-29 | PR [#868](https://github.com/digitaldemocracy2030/kouchou-ai/pull/868)（ユーザー API キーの受け渡しの修正）で混入 |
| 2026-10-13 | v4.1.0 リリース（問題を含む） |
| 2026-10-18 | コードレビューで発見 |
| 2026-10-26 | 修正 PR #1136 を merge。v4.2.0 と `kouchou-ai-analysis-core` 0.2.0 をリリース |
