# Azure Container Apps 移行メモ (client* -> public-viewer/admin/static-site-builder)

- 日付: 2026-02-07
- リソースグループ: `dd2030-kouchouai-demo-rg`
- サブスクリプション: `kouchou-ai` (`079e8ef5-7461-407d-84b6-b4f37b9f31c1`)
- Container Apps 環境: `kouchouai-demo-container-env`

## nishioの作業

Azure環境のリファクタリング後の構成への変更について

- 1: Azure環境 `c4jadmindd2030.onmicrosoft.com` へのアクセス権をもらい ​​https://portal.azure.com/#@c4jadmindd2030.onmicrosoft.com/resource/subscriptions/079e8ef5-7461-407d-84b6-b4f37b9f31c1/resourceGroups/dd2030-kouchouai-demo-rg/overview でリソースグループを見ることができるのを確認
 
- 2: az login --tenant c4jadmindd2030.onmicrosoft.com でCodexにログインさせる
- 3: 作業(詳細は下記)
- 4: GitHub ActionのAzure Deploymentをre-runしてsuccessするのを確認: https://github.com/digitaldemocracy2030/kouchou-ai/actions/runs/21740920722/job/62820695796
- 5: 管理画面を確認、既存のレポートはStorageから復元されているようだ


## 概要
- 旧名称の Container Apps (`client`, `client-admin`, `client-static-build`) を新名称 (`public-viewer`, `admin`, `static-site-builder`) へ移行しました。
- 既存の ACR イメージを使って新アプリを作成し、旧アプリのシークレットをコピーしました。
- 新ドメインに合わせて環境変数を更新し、シークレット反映のため再起動しました。
- 旧アプリは削除しました。

## 発生原因
- GitHub Actions と Makefile は新名称 (`public-viewer`, `admin`, `static-site-builder`) を前提にしていました。
- Azure 側に旧名称 (`client*`) しか存在せず、`az containerapp show` などが `does not exist` で失敗していました。

## 実施内容
- 正しいテナント/サブスクリプションにログイン。
- 新規 Container Apps を作成。
- 旧アプリからシークレットを取得して新アプリへ登録。
- 新ドメインを使うように環境変数を更新。
- シークレット反映のため全アプリを再起動。
- 旧アプリを削除。

## 現在の状態
- `api`: `https://api.wittyisland-cc57c95f.japaneast.azurecontainerapps.io`
- `public-viewer`: `https://public-viewer.wittyisland-cc57c95f.japaneast.azurecontainerapps.io`
- `admin`: `https://admin.wittyisland-cc57c95f.japaneast.azurecontainerapps.io`
- `static-site-builder`: `https://static-site-builder.internal.wittyisland-cc57c95f.japaneast.azurecontainerapps.io`

## 実行コマンド（マスク済み）
代表的な実行内容のみ抜粋しています。値はすべてマスク済みです。

```bash
# ログイン
az login --tenant c4jadmindd2030.onmicrosoft.com
az account set --subscription 079e8ef5-7461-407d-84b6-b4f37b9f31c1

# 現状確認
az containerapp list -g dd2030-kouchouai-demo-rg -o table

# 新アプリ作成
az containerapp create --name public-viewer --resource-group dd2030-kouchouai-demo-rg \
  --environment kouchouai-demo-container-env --image dd2030kouchouai.azurecr.io/public-viewer:latest \
  --registry-server dd2030kouchouai.azurecr.io --registry-username dd2030kouchouai --registry-password <acr-password> \
  --target-port 3000 --ingress external --min-replicas 1

az containerapp create --name admin --resource-group dd2030-kouchouai-demo-rg \
  --environment kouchouai-demo-container-env --image dd2030kouchouai.azurecr.io/admin:latest \
  --registry-server dd2030kouchouai.azurecr.io --registry-username dd2030kouchouai --registry-password <acr-password> \
  --target-port 4000 --ingress external --min-replicas 1

az containerapp create --name static-site-builder --resource-group dd2030-kouchouai-demo-rg \
  --environment kouchouai-demo-container-env --image dd2030kouchouai.azurecr.io/static-site-builder:latest \
  --registry-server dd2030kouchouai.azurecr.io --registry-username dd2030kouchouai --registry-password <acr-password> \
  --target-port 3200 --ingress internal --min-replicas 1

# シークレット設定（値は省略）
az containerapp secret set --name public-viewer --resource-group dd2030-kouchouai-demo-rg --secrets \
  public-api-key=<value> revalidate-secret=<value>

az containerapp secret set --name admin --resource-group dd2030-kouchouai-demo-rg --secrets \
  admin-api-key=<value> basic-auth-username=<value> basic-auth-password=<value>

az containerapp secret set --name static-site-builder --resource-group dd2030-kouchouai-demo-rg --secrets \
  public-api-key=<value>

# 環境変数更新
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

# 再起動
az containerapp update --name public-viewer --resource-group dd2030-kouchouai-demo-rg --min-replicas 0
az containerapp update --name public-viewer --resource-group dd2030-kouchouai-demo-rg --min-replicas 1
# admin / static-site-builder / api も同様

# 旧アプリ削除
az containerapp delete --name client --resource-group dd2030-kouchouai-demo-rg --yes
az containerapp delete --name client-admin --resource-group dd2030-kouchouai-demo-rg --yes
az containerapp delete --name client-static-build --resource-group dd2030-kouchouai-demo-rg --yes
```

## フォローアップ推奨
- GitHub Actions の `Azure Deployment` を再実行して、新ドメインを `NEXT_PUBLIC_*` に焼き込んだイメージを再ビルドしてください。
- 必要に応じて `make azure-apply-policies` でヘルスチェック/ポリシーを適用してください（`.env.azure` が必要）。

## 注意点
- シークレット値はログに出力せずに移行しています。
- `static-site-builder` は内部向けのままです。
