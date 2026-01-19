#!/bin/bash

# スクリプトの説明
echo "Azure Blob Storageへのアクセス権限を付与するスクリプト"
echo "このスクリプトは現在ログインしているユーザーにStorage Blob Data Contributorロールを付与します"
echo "-------------------------------------------------------------------"

# 環境変数の読み込み
if [ -f .env ]; then
  echo "環境変数を.envファイルから読み込みます..."
  export $(grep -v '^#' .env | xargs)
fi

if [ -f .env.azure ]; then
  echo "環境変数を.env.azureファイルから読み込みます..."
  export $(grep -v '^#' .env.azure | xargs)
fi

# 必要な変数の確認
if [ -z "$AZURE_RESOURCE_GROUP" ]; then
  echo "エラー: AZURE_RESOURCE_GROUP が設定されていません。"
  echo ".env または .env.azure ファイルで設定してください。"
  exit 1
fi

if [ -z "$AZURE_BLOB_STORAGE_ACCOUNT_NAME" ]; then
  echo "エラー: AZURE_BLOB_STORAGE_ACCOUNT_NAME が設定されていません。"
  echo ".env または .env.azure ファイルで設定してください。"
  exit 1
fi

# サブスクリプションIDの取得
echo "現在のサブスクリプションIDを取得しています..."
SUBSCRIPTION_ID=$(az account show --query id -o tsv)
if [ -z "$SUBSCRIPTION_ID" ]; then
  echo "エラー: サブスクリプションIDの取得に失敗しました。"
  echo "Azure CLIでログインしているか確認してください: az login"
  exit 1
fi

# ユーザーIDの取得
echo "現在ログインしているユーザーのIDを取得しています..."
USER_ID=$(az ad signed-in-user show --query id -o tsv)
if [ -z "$USER_ID" ]; then
  echo "エラー: ユーザーIDの取得に失敗しました。"
  echo "Azure CLIでログインしているか確認してください: az login"
  exit 1
fi

# 変数の表示
echo "-------------------------------------------------------------------"
echo "使用する設定:"
echo "サブスクリプションID: $SUBSCRIPTION_ID"
echo "リソースグループ: $AZURE_RESOURCE_GROUP"
echo "ストレージアカウント: $AZURE_BLOB_STORAGE_ACCOUNT_NAME"
echo "ユーザーID: $USER_ID"
echo "-------------------------------------------------------------------"

# 確認
read -p "上記の設定でロールを割り当てますか？ (y/n): " confirm
if [ "$confirm" != "y" ]; then
  echo "キャンセルしました。"
  exit 0
fi

# ロールの割り当て
echo "ストレージアカウントへのアクセス権を付与しています..."
az role assignment create \
  --role "Storage Blob Data Contributor" \
  --assignee "$USER_ID" \
  --scope "/subscriptions/$SUBSCRIPTION_ID/resourceGroups/$AZURE_RESOURCE_GROUP/providers/Microsoft.Storage/storageAccounts/$AZURE_BLOB_STORAGE_ACCOUNT_NAME"

RESULT=$?
if [ $RESULT -eq 0 ]; then
  echo "-------------------------------------------------------------------"
  echo "ロールの割り当てが完了しました。"
  echo "これでAzure Blob Storageへのアップロードが可能になります。"
else
  echo "-------------------------------------------------------------------"
  echo "エラー: ロールの割り当てに失敗しました。"
  echo "Azure CLIの出力を確認してください。"
  exit $RESULT
fi
