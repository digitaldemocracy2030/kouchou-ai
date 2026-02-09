# Azure Container Apps 移行メモ (client* -> public-viewer/admin/static-site-builder)

- 日付: 2026-02-07
- リソースグループ: `dd2030-kouchouai-demo-rg`
- サブスクリプション: `kouchou-ai` (`079e8ef5-7461-407d-84b6-b4f37b9f31c1`)
- Container Apps 環境: `kouchouai-demo-container-env`
- 関連ドキュメント: `docs/refactoring/naming_convention.md`

## 目的
- リファクタ後の命名規約に合わせて Azure 上の Container Apps 名を揃える
- GitHub Actions `Azure Deployment` が失敗しない状態に戻す

## 事前状況（問題）
- Azure 側に旧名称の Container Apps しか存在しない:
  - `api`, `client`, `client-admin`, `client-static-build`
- リポジトリ側（Makefile / GitHub Actions）は新名称を前提:
  - `public-viewer`, `admin`, `static-site-builder`
- その結果、デプロイ時に `az containerapp show/update/secret set` が `... does not exist` で失敗する

## 実施した移行作業（Azure 側）
### 1) ログイン

```bash
az login --tenant c4jadmindd2030.onmicrosoft.com
az account set --subscription 079e8ef5-7461-407d-84b6-b4f37b9f31c1
```

### 2) 現状確認

```bash
az containerapp list -g dd2030-kouchouai-demo-rg -o table
az containerapp env list -g dd2030-kouchouai-demo-rg -o table
```

### 3) 新名称の Container Apps を作成
既存の ACR イメージを使って新アプリを作成（旧アプリは残したまま）。

```bash
az containerapp create --name public-viewer --resource-group dd2030-kouchouai-demo-rg \
  --environment kouchouai-demo-container-env \
  --image dd2030kouchouai.azurecr.io/public-viewer:latest \
  --registry-server dd2030kouchouai.azurecr.io \
  --registry-username dd2030kouchouai \
  --registry-password <acr-password> \
  --target-port 3000 --ingress external --min-replicas 1

az containerapp create --name admin --resource-group dd2030-kouchouai-demo-rg \
  --environment kouchouai-demo-container-env \
  --image dd2030kouchouai.azurecr.io/admin:latest \
  --registry-server dd2030kouchouai.azurecr.io \
  --registry-username dd2030kouchouai \
  --registry-password <acr-password> \
  --target-port 4000 --ingress external --min-replicas 1

az containerapp create --name static-site-builder --resource-group dd2030-kouchouai-demo-rg \
  --environment kouchouai-demo-container-env \
  --image dd2030kouchouai.azurecr.io/static-site-builder:latest \
  --registry-server dd2030kouchouai.azurecr.io \
  --registry-username dd2030kouchouai \
  --registry-password <acr-password> \
  --target-port 3200 --ingress internal --min-replicas 1
```

### 4) シークレット移設（旧アプリ -> 新アプリ）
注意:
- `az containerapp secret list` はデフォルトで値を返さないため、コピー用途では `--show-values` が必須
- `secret set` の後は **コンテナ再起動が必要**（Azure CLI が warning を出す）

```bash
# 旧アプリからシークレット値を取得（例）
az containerapp secret list --name client --resource-group dd2030-kouchouai-demo-rg --show-values
az containerapp secret list --name client-admin --resource-group dd2030-kouchouai-demo-rg --show-values
az containerapp secret list --name api --resource-group dd2030-kouchouai-demo-rg --show-values

# 新アプリへ設定（値はマスク）
az containerapp secret set --name public-viewer --resource-group dd2030-kouchouai-demo-rg --secrets \
  public-api-key=<value> revalidate-secret=<value>

az containerapp secret set --name admin --resource-group dd2030-kouchouai-demo-rg --secrets \
  admin-api-key=<value> basic-auth-username=<value> basic-auth-password=<value>

az containerapp secret set --name static-site-builder --resource-group dd2030-kouchouai-demo-rg --secrets \
  public-api-key=<value>
```

### 5) 環境変数の更新
ポイント:
- `secretref:` を使って secret を環境変数に紐付ける
- `api` の `REVALIDATE_URL` は `public-viewer` の新 FQDN に合わせて更新

```bash
az containerapp update --name public-viewer --resource-group dd2030-kouchouai-demo-rg --set-env-vars \
  NEXT_PUBLIC_PUBLIC_API_KEY=secretref:public-api-key \
  NEXT_PUBLIC_API_BASEPATH=https://api.wittyisland-cc57c95f.japaneast.azurecontainerapps.io \
  API_BASEPATH=https://api.wittyisland-cc57c95f.japaneast.azurecontainerapps.io \
  REVALIDATE_SECRET=secretref:revalidate-secret

az containerapp update --name admin --resource-group dd2030-kouchouai-demo-rg --set-env-vars \
  NEXT_PUBLIC_ADMIN_API_KEY=secretref:admin-api-key \
  NEXT_PUBLIC_CLIENT_BASEPATH=https://public-viewer.wittyisland-cc57c95f.japaneast.azurecontainerapps.io \
  NEXT_PUBLIC_API_BASEPATH=https://api.wittyisland-cc57c95f.japaneast.azurecontainerapps.io \
  API_BASEPATH=https://api.wittyisland-cc57c95f.japaneast.azurecontainerapps.io \
  CLIENT_STATIC_BUILD_BASEPATH=https://static-site-builder.internal.wittyisland-cc57c95f.japaneast.azurecontainerapps.io \
  BASIC_AUTH_USERNAME=secretref:basic-auth-username \
  BASIC_AUTH_PASSWORD=secretref:basic-auth-password

az containerapp update --name static-site-builder --resource-group dd2030-kouchouai-demo-rg --set-env-vars \
  NEXT_PUBLIC_PUBLIC_API_KEY=secretref:public-api-key \
  NEXT_PUBLIC_API_BASEPATH=https://api.wittyisland-cc57c95f.japaneast.azurecontainerapps.io \
  API_BASEPATH=https://api.wittyisland-cc57c95f.japaneast.azurecontainerapps.io

az containerapp update --name api --resource-group dd2030-kouchouai-demo-rg --set-env-vars \
  REVALIDATE_URL=https://public-viewer.wittyisland-cc57c95f.japaneast.azurecontainerapps.io/api/revalidate \
  REVALIDATE_SECRET=secretref:revalidate-secret
```

### 6) 再起動（secret 反映）

```bash
for app in public-viewer admin static-site-builder api; do
  az containerapp update --name "$app" --resource-group dd2030-kouchouai-demo-rg --min-replicas 0
  sleep 5
  az containerapp update --name "$app" --resource-group dd2030-kouchouai-demo-rg --min-replicas 1
done
```

### 7) 旧アプリ削除
旧名称の Container App は rename 不可のため削除。

```bash
az containerapp delete --name client --resource-group dd2030-kouchouai-demo-rg --yes
az containerapp delete --name client-admin --resource-group dd2030-kouchouai-demo-rg --yes
az containerapp delete --name client-static-build --resource-group dd2030-kouchouai-demo-rg --yes
```

### 8) 動作確認

```bash
az containerapp list -g dd2030-kouchouai-demo-rg -o table
curl -f "https://api.wittyisland-cc57c95f.japaneast.azurecontainerapps.io/" --max-time 15
curl -f "https://public-viewer.wittyisland-cc57c95f.japaneast.azurecontainerapps.io/" --max-time 15
```

## 移行後に発生した問題と恒久対策（リポジトリ側）
### public-viewer が stream timeout になる（起動できない）
原因:
- `apps/public-viewer/entrypoint.sh` が **起動時に `pnpm run build` を実行**する
- その `next build` が Turbopack の workspace root 推論に失敗すると、コンテナが起動できず viewer がタイムアウトする

対策（実装済み）:
- PR #784: `apps/public-viewer/next.config.ts` に `turbopack.root` を明示（root 推論に依存しない）
- PR #782: `apps/public-viewer/Dockerfile` の runner イメージに monorepo ルート情報（`package.json` / `pnpm-workspace.yaml` / `.npmrc`）をコピー
- PR #782: `apps/public-viewer/entrypoint.sh` に `set -e` を入れて、ビルド失敗を即座にコンテナ失敗として扱う

診断用コマンド:

```bash
az containerapp logs show --name public-viewer --resource-group dd2030-kouchouai-demo-rg --tail 200
az containerapp revision list --name public-viewer --resource-group dd2030-kouchouai-demo-rg -o table
```

### CI のヘルスチェックが早すぎて false negative になる
原因:
- `public-viewer` は起動時に build するため、デプロイ直後は数分 200 を返せない場合がある（レポート数により変動）

対策（実装済み）:
- PR #785: `.github/workflows/azure-deploy.yml` のヘルスチェックを以下のように改善
  - リトライ回数を増加（6回 -> 15回）
  - 各試行で API/viewer の HTTP ステータスをログ出力
  - 失敗時に最新 revision の health/running/details をログ出力

## 現在の構成（2026-02-07 時点）
- `api`: `https://api.wittyisland-cc57c95f.japaneast.azurecontainerapps.io`
- `public-viewer`: `https://public-viewer.wittyisland-cc57c95f.japaneast.azurecontainerapps.io`
- `admin`: `https://admin.wittyisland-cc57c95f.japaneast.azurecontainerapps.io`
- `static-site-builder`（internal）: `https://static-site-builder.internal.wittyisland-cc57c95f.japaneast.azurecontainerapps.io`

## 運用メモ
- admin の Basic 認証は `admin` Container App の secrets にある:
  - `basic-auth-username`
  - `basic-auth-password`
- `static-site-builder` は internal ingress のため、外部ネットワークから直接アクセスできない
- `public-viewer` は起動時 build のため、環境変数変更を確実に反映したい場合はコンテナ再起動（新 revision 作成）を行う
