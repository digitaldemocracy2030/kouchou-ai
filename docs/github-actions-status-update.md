# Issueのstatus自動更新の設定手順

このドキュメントでは、GitHub AppsとGitHub Actionsを用いてProjectsのstatusフィールドを自動更新するためのセットアップ手順を説明します。

### OrganizationのGitHub Apps を作成する
- 手順：https://docs.github.com/ja/apps/creating-github-apps/registering-a-github-app/registering-a-github-app
- WebhookはOFF
- Permissions > Organization permissions > Projects > Read and write を指定
- Permissions > Repository permissions > Metadata > Read only を指定
- Permissions > Repository permissions > Actions > Read only を指定
    - 確認メールが届いたら、リンク先でリポジトリを指定して許可
- Install only on this account

### Private Key の発行
- 作成完了画面の指示に従い、続けてGitHub Apps のインストール準備としてprivate keyを発行する
- 手順：https://docs.github.com/ja/apps/creating-github-apps/authenticating-with-a-github-app/managing-private-keys-for-github-apps
- 発行すると、ローカルに秘密鍵（pemファイル）がダウンロードされる

### OrganizationのGitHub Apps をインストールする
- 手順：https://docs.github.com/ja/apps/using-github-apps/installing-your-own-github-app
- General > Generate a new client secret
- Install App > Install (to organization)

### Organization secrets の設定
- Organization の設定ページを開く
- Repository > Settings > General > Security > Secrets and variables > Actions > Organization secrets
- PJ_APP_ID : AppのGeneralタブのApp ID
- PJ_APP_PEM : private key を発行した際にローカルにダウンロードされたpemファイルの内容（テキスト全体）
    - Repository を指定する

# 補足：

- `.github/scripts/repo_config.py` について
    - `digitaldemocracy2030/kouchou-ai` に特化したID等になっている
    - 機密情報ではない
    - 本来は環境設定に持たせるかscript内で取得する方が綺麗だが、どうせ後続処理もこのリポジトリ独自のルールに則った処理なので、このままにしている
    - `project_id` (PVT_xxxx) と `status_field_id` (PVTSSF_xxxx) の確認方法：
        - https://docs.github.com/ja/graphql/overview/explorer にアクセス
        - Githubアカウントでログイン ※ `digitaldemocracy2030` のメンバーである必要がある
        - 以下のクエリを実行:
```
{
  organization(login: "digitaldemocracy2030") {
    projectV2(number: 3) {
      id
      fields(first: 20) {
        nodes {
          ... on ProjectV2SingleSelectField {
            id
            name
          }
        }
      }
    }
  }
}
```