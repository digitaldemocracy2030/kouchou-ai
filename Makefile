.PHONY: build up down \
lint/server-check lint/server-format \
client-build-static client-setup client-dev client-dev-server client-admin-dev-server dummy-server \
azure-cli azure-login azure-build azure-push azure-deploy azure-info azure-config-update azure-cleanup azure-status prepare-yaml azure-save-env azure-apply-policies \
azure-logs-public-viewer azure-logs-api azure-logs-admin azure-logs-static-site-builder

##############################################################################
# envファイル変更チェック機能
##############################################################################

HASH_DIR := .env-hashes

ENV_HASH_FILE := $(HASH_DIR)/.env.hash
AZURE_ENV_HASH_FILE := $(HASH_DIR)/.env.azure.hash

define check_env_changes
changed=false; \
if [ -f .env ]; then \
	if command -v sha256sum >/dev/null 2>&1; then \
		current_hash=$$(sha256sum .env | cut -d' ' -f1); \
	else \
		current_hash=$$(shasum -a 256 .env | cut -d' ' -f1); \
	fi; \
	stored_hash=$$([ -f $(ENV_HASH_FILE) ] && cat $(ENV_HASH_FILE) || echo "no_hash"); \
	if [ "$$current_hash" != "$$stored_hash" ]; then \
		changed=true; \
	fi; \
fi; \
if [ -f .env.azure ]; then \
	if command -v sha256sum >/dev/null 2>&1; then \
		current_hash=$$(sha256sum .env.azure | cut -d' ' -f1); \
	else \
		current_hash=$$(shasum -a 256 .env.azure | cut -d' ' -f1); \
	fi; \
	stored_hash=$$([ -f $(AZURE_ENV_HASH_FILE) ] && cat $(AZURE_ENV_HASH_FILE) || echo "no_hash"); \
	if [ "$$current_hash" != "$$stored_hash" ]; then \
		changed=true; \
	fi; \
fi
endef

define update_env_hashes
mkdir -p $(HASH_DIR); \
if [ -f .env ]; then sha256sum .env | cut -d' ' -f1 > $(ENV_HASH_FILE); fi; \
if [ -f .env.azure ]; then sha256sum .env.azure | cut -d' ' -f1 > $(AZURE_ENV_HASH_FILE); fi
endef

define build_with_env_check
$(check_env_changes); \
if [ "$$changed" = "true" ]; then \
	echo "envファイルの変更が検出されました。再ビルドを実行します..."; \
	docker compose down 2>/dev/null || true; \
	docker compose build --no-cache; \
	$(update_env_hashes); \
	echo "再ビルド完了"; \
else \
	echo "envファイルに変更はありません。通常ビルドを実行します..."; \
	docker compose build; \
fi
endef

$(HASH_DIR):
	@mkdir -p $(HASH_DIR)

check-env-status:
	@echo "🔍 envファイルの変更状況:"
	@echo "----------------------------------------"
	@if [ -f .env ]; then \
		current_hash=$$(sha256sum .env | cut -d' ' -f1); \
		stored_hash=$$([ -f $(ENV_HASH_FILE) ] && cat $(ENV_HASH_FILE) || echo "no_hash"); \
		if [ "$$current_hash" != "$$stored_hash" ]; then \
			echo ".env: 変更あり"; \
		else \
			echo ".env: 変更なし"; \
		fi; \
	else \
		echo ".env: ファイルなし"; \
	fi
	@if [ -f .env.azure ]; then \
		current_hash=$$(sha256sum .env.azure | cut -d' ' -f1); \
		stored_hash=$$([ -f $(AZURE_ENV_HASH_FILE) ] && cat $(AZURE_ENV_HASH_FILE) || echo "no_hash"); \
		if [ "$$current_hash" != "$$stored_hash" ]; then \
			echo ".env.azure: 変更あり"; \
		else \
			echo ".env.azure: 変更なし"; \
		fi; \
	else \
		echo ".env.azure: ファイルなし"; \
	fi
	@echo "----------------------------------------"

update-hashes: | $(HASH_DIR)
	@$(update_env_hashes)
	@echo ".envファイルのハッシュを更新しました"

clean-env-hashes:
	@echo ">>> envファイルのハッシュをクリーンアップ中..."
	@rm -rf $(HASH_DIR)
	@echo "ハッシュファイルをクリーンアップしました"

##############################################################################
# ローカル開発環境のコマンド
##############################################################################

build:
	@$(build_with_env_check)

up:
	@$(build_with_env_check)
	docker compose up

build-force:
	@echo ">>> チェックをスキップしてビルド..."
	docker compose build

up-force:
	@echo ">>> チェックをスキップして起動..."
	docker compose up --build

down:
	docker compose down

client-build-static:
	rm -rf out
	docker compose up -d --wait api
	docker compose run --rm -e BASE_PATH=$(NEXT_PUBLIC_STATIC_EXPORT_BASE_PATH) -e NEXT_PUBLIC_OUTPUT_MODE=export -v $(shell pwd)/apps/api:/repo/apps/api -v $(shell pwd)/out:/repo/apps/public-viewer/dist public-viewer sh -c "pnpm run build:static && cp -r out/* dist && touch dist/.nojekyll"
	docker compose down

client-setup:
	pnpm install
	cd apps/public-viewer && cp .env-sample .env
	cd apps/admin && cp .env-sample .env
	cd utils/dummy-server && pnpm install && cp .env-sample .env

client-dev: client-dev-server client-admin-dev-server dummy-server

client-dev-server:
	pnpm --filter @kouchou-ai/public-viewer dev

client-admin-dev-server:
	pnpm --filter @kouchou-ai/admin dev

dummy-server:
	cd utils/dummy-server && pnpm dev

# Docker環境でのlint/check, format
lint/api-check:
	docker compose run --rm api python -m ruff check .
	docker compose run --rm api python -m ruff format . --diff

lint/api-format:
	docker compose run --rm api python -m ruff format .
	docker compose run --rm api python -m ruff check . --fix

test/api:
	docker compose run --rm api pytest tests/

##############################################################################
# Azure初期デプロイのコマンド
##############################################################################

define read-env
$(eval include .env)
$(eval -include .env.azure)
$(eval AZURE_RESOURCE_GROUP ?= kouchou-ai-rg)
$(eval AZURE_LOCATION ?= japaneast)
$(eval AZURE_CONTAINER_ENV ?= kouchou-ai-env)
$(eval AZURE_WORKSPACE_NAME ?= kouchou-ai-logs)
$(eval AZURE_ACR_NAME ?= kouchouai$(shell date +%s | sha256sum | head -c 8))
$(eval AZURE_ACR_SKU ?= Basic)
$(eval export)
endef

# Azureコンテナを起動（対話モード）
azure-cli:
	docker run -it --rm -v $(shell pwd):/workspace -w /workspace mcr.microsoft.com/azure-cli bash

# Azureにログイン
azure-login:
	docker run -it --rm -v $(shell pwd):/workspace -v $(HOME)/.azure:/root/.azure -w /workspace mcr.microsoft.com/azure-cli az login

# Azureリソースグループの作成
azure-setup:
	$(call read-env)
	docker run -it --rm -v $(shell pwd):/workspace -v $(HOME)/.azure:/root/.azure -w /workspace mcr.microsoft.com/azure-cli /bin/bash -c "\
	    echo '>>> リソース名情報:' && \
	    echo '>>> リソースグループ: $(AZURE_RESOURCE_GROUP)' && \
	    echo '>>> ロケーション: $(AZURE_LOCATION)' && \
	    echo '>>> コンテナレジストリ: $(AZURE_ACR_NAME)' && \
	    az group create --name $(AZURE_RESOURCE_GROUP) --location $(AZURE_LOCATION) && \
	    az acr create --resource-group $(AZURE_RESOURCE_GROUP) --name $(AZURE_ACR_NAME) --sku $(AZURE_ACR_SKU) && \
	    echo '>>> 設定されたACR名を.env.azureに保存しています...' && \
	    echo 'AZURE_ACR_NAME=$(AZURE_ACR_NAME)' > /workspace/.env.azure.generated"

# ストレージの作成
azure-create-storage:
	$(call read-env)
	docker run -it --rm -v $(shell pwd):/workspace -v $(HOME)/.azure:/root/.azure -w /workspace mcr.microsoft.com/azure-cli /bin/bash -c "\
	    echo '>>> Microsoft.Storageプロバイダーの状態を確認中...' && \
	    PROVIDER_STATE=\$$(az provider show --namespace Microsoft.Storage --query registrationState -o tsv 2>/dev/null || echo 'NotRegistered') && \
	    if [ \"\$$PROVIDER_STATE\" != \"Registered\" ]; then \
	        echo '>>> Microsoft.Storageプロバイダーを登録中...' && \
	        az provider register --namespace Microsoft.Storage && \
	        echo '>>> Microsoft.Storageの登録を待機中...' && \
	        while [ \$$(az provider show --namespace Microsoft.Storage --query registrationState -o tsv) != \"Registered\" ]; do \
	            echo \"   - 登録処理を待機中...\" && sleep 5; \
	        done; \
	    else \
	        echo '>>> Microsoft.Storageプロバイダーは既に登録されています。'; \
	    fi && \
	    echo '>>> ストレージアカウントの作成...' && \
	    az storage account create \
	        --name $(AZURE_BLOB_STORAGE_ACCOUNT_NAME) \
	        --resource-group $(AZURE_RESOURCE_GROUP) \
	        --location $(AZURE_LOCATION) \
	        --sku Standard_LRS && \
	    echo '>>> ストレージコンテナの作成...' && \
	    az storage container create \
	        --account-name $(AZURE_BLOB_STORAGE_ACCOUNT_NAME) \
	        --name $(AZURE_BLOB_STORAGE_CONTAINER_NAME) \
	        --public-access off"

# ACRに自動ログイン
azure-acr-login-auto:
	$(call read-env)
	@echo ">>> ACRに自動ログイン中..."
	$(eval ACR_TOKEN=$(shell docker run --rm -v $(HOME)/.azure:/root/.azure mcr.microsoft.com/azure-cli az acr login --name $(AZURE_ACR_NAME) --expose-token --query accessToken -o tsv))
	@docker login $(AZURE_ACR_NAME).azurecr.io --username 00000000-0000-0000-0000-000000000000 --password $(ACR_TOKEN)

# Azure用のイメージをビルド
azure-build:
	$(call read-env)
	@$(check_env_changes); \
	if [ "$$changed" = "true" ]; then \
		echo "envファイルの変更が検出されました。Azure用イメージを再ビルドします...(no-cache)"; \
		docker build --platform linux/amd64 --no-cache \
			-f ./apps/api/Dockerfile \
			-t $(AZURE_ACR_NAME).azurecr.io/api:latest . && \
		docker build --platform linux/amd64 --no-cache \
			--build-arg NEXT_PUBLIC_API_BASEPATH="$(NEXT_PUBLIC_API_BASEPATH)" \
			--build-arg NEXT_PUBLIC_PUBLIC_API_KEY="$(NEXT_PUBLIC_PUBLIC_API_KEY)" \
			--build-arg NEXT_PUBLIC_SITE_URL="$(NEXT_PUBLIC_SITE_URL)" \
			--build-arg API_BASEPATH="$(API_BASEPATH)" \
			-f ./apps/public-viewer/Dockerfile \
			-t $(AZURE_ACR_NAME).azurecr.io/public-viewer:latest . && \
		docker build --platform linux/amd64 --no-cache \
			--build-arg NEXT_PUBLIC_CLIENT_BASEPATH="$(NEXT_PUBLIC_CLIENT_BASEPATH)" \
			--build-arg NEXT_PUBLIC_ADMIN_API_KEY="$(NEXT_PUBLIC_ADMIN_API_KEY)" \
			--build-arg NEXT_PUBLIC_API_BASEPATH="$(NEXT_PUBLIC_API_BASEPATH)" \
			--build-arg CLIENT_STATIC_BUILD_BASEPATH="$(CLIENT_STATIC_BUILD_BASEPATH)" \
			-f ./apps/admin/Dockerfile \
			-t $(AZURE_ACR_NAME).azurecr.io/admin:latest . && \
		docker build --platform linux/amd64 --no-cache \
			-t $(AZURE_ACR_NAME).azurecr.io/static-site-builder:latest \
			-f ./apps/static-site-builder/Dockerfile . && \
		$(update_env_hashes); \
	else \
		echo "envファイルに変更はありません。Azure用イメージをビルドします..."; \
		docker build --platform linux/amd64 \
			-f ./apps/api/Dockerfile \
			-t $(AZURE_ACR_NAME).azurecr.io/api:latest .; \
		docker build --platform linux/amd64 \
			--build-arg NEXT_PUBLIC_API_BASEPATH="$(NEXT_PUBLIC_API_BASEPATH)" \
			--build-arg NEXT_PUBLIC_PUBLIC_API_KEY="$(NEXT_PUBLIC_PUBLIC_API_KEY)" \
			--build-arg NEXT_PUBLIC_SITE_URL="$(NEXT_PUBLIC_SITE_URL)" \
			--build-arg API_BASEPATH="$(API_BASEPATH)" \
			-f ./apps/public-viewer/Dockerfile \
			-t $(AZURE_ACR_NAME).azurecr.io/public-viewer:latest .; \
		docker build --platform linux/amd64 \
			--build-arg NEXT_PUBLIC_CLIENT_BASEPATH="$(NEXT_PUBLIC_CLIENT_BASEPATH)" \
			--build-arg NEXT_PUBLIC_ADMIN_API_KEY="$(NEXT_PUBLIC_ADMIN_API_KEY)" \
			--build-arg NEXT_PUBLIC_API_BASEPATH="$(NEXT_PUBLIC_API_BASEPATH)" \
			--build-arg CLIENT_STATIC_BUILD_BASEPATH="$(CLIENT_STATIC_BUILD_BASEPATH)" \
			-f ./apps/admin/Dockerfile \
			-t $(AZURE_ACR_NAME).azurecr.io/admin:latest .; \
		docker build --platform linux/amd64 \
			-t $(AZURE_ACR_NAME).azurecr.io/static-site-builder:latest \
			-f ./apps/static-site-builder/Dockerfile .; \
	fi

# イメージをAzureにプッシュ（ローカルのDockerから）
azure-push:
	$(call read-env)
	docker push $(AZURE_ACR_NAME).azurecr.io/api:latest
	docker push $(AZURE_ACR_NAME).azurecr.io/public-viewer:latest
	docker push $(AZURE_ACR_NAME).azurecr.io/admin:latest
	docker push $(AZURE_ACR_NAME).azurecr.io/static-site-builder:latest

# Container Apps環境の作成とデプロイ
azure-deploy:
	$(call read-env)
	@echo ">>> YAMLテンプレートを準備..."
	@$(MAKE) prepare-yaml
	docker run -it --rm -v $(shell pwd):/workspace -v $(HOME)/.azure:/root/.azure -w /workspace mcr.microsoft.com/azure-cli /bin/bash -c "\
	    az extension add --name containerapp --upgrade && \
	    az provider register --namespace Microsoft.App && \
	    az provider register --namespace Microsoft.OperationalInsights --wait && \
	    echo '>>> Log Analytics ワークスペースの作成...' && \
	    az monitor log-analytics workspace create \
	        --resource-group $(AZURE_RESOURCE_GROUP) \
	        --workspace-name $(AZURE_WORKSPACE_NAME) \
	        --location $(AZURE_LOCATION) && \
	    WORKSPACE_ID=\$$(az monitor log-analytics workspace show \
	        --resource-group $(AZURE_RESOURCE_GROUP) \
	        --workspace-name $(AZURE_WORKSPACE_NAME) \
	        --query customerId -o tsv) && \
	    echo '>>> Container Apps環境の作成...' && \
	    az containerapp env create \
	        --name $(AZURE_CONTAINER_ENV) \
	        --resource-group $(AZURE_RESOURCE_GROUP) \
	        --location $(AZURE_LOCATION) \
	        --logs-workspace-id \$$WORKSPACE_ID && \
	    echo '>>> ACRへのアクセス権の設定...' && \
	    az acr update \
	        --name $(AZURE_ACR_NAME) \
	        --resource-group $(AZURE_RESOURCE_GROUP) \
	        --admin-enabled true && \
	    ACR_PASSWORD=\$$(az acr credential show \
	        --name $(AZURE_ACR_NAME) \
	        --resource-group $(AZURE_RESOURCE_GROUP) \
	        --query passwords[0].value -o tsv) && \
	    echo '>>> APIコンテナのデプロイ...' && \
	    az containerapp create \
	        --name api \
	        --resource-group $(AZURE_RESOURCE_GROUP) \
	        --environment $(AZURE_CONTAINER_ENV) \
	        --image $(AZURE_ACR_NAME).azurecr.io/api:latest \
	        --registry-server $(AZURE_ACR_NAME).azurecr.io \
	        --registry-username $(AZURE_ACR_NAME) \
	        --registry-password \$$ACR_PASSWORD \
	        --target-port 8000 \
	        --ingress external \
	        --min-replicas 1 && \
	    echo '>>> 公開閲覧用コンテナのデプロイ...' && \
	    az containerapp create \
	        --name public-viewer \
	        --resource-group $(AZURE_RESOURCE_GROUP) \
	        --environment $(AZURE_CONTAINER_ENV) \
	        --image $(AZURE_ACR_NAME).azurecr.io/public-viewer:latest \
	        --registry-server $(AZURE_ACR_NAME).azurecr.io \
	        --registry-username $(AZURE_ACR_NAME) \
	        --registry-password \$$ACR_PASSWORD \
	        --target-port 3000 \
	        --ingress external \
	        --min-replicas 1 && \
	    echo '>>> 管理画面コンテナのデプロイ...' && \
	    az containerapp create \
	        --name admin \
	        --resource-group $(AZURE_RESOURCE_GROUP) \
	        --environment $(AZURE_CONTAINER_ENV) \
	        --image $(AZURE_ACR_NAME).azurecr.io/admin:latest \
	        --registry-server $(AZURE_ACR_NAME).azurecr.io \
	        --registry-username $(AZURE_ACR_NAME) \
	        --registry-password \$$ACR_PASSWORD \
	        --target-port 4000 \
	        --ingress external \
	        --min-replicas 1 && \
	    echo '>>> 静的サイトビルダーコンテナのデプロイ...' && \
	    az containerapp create \
	        --name static-site-builder \
	        --resource-group $(AZURE_RESOURCE_GROUP) \
	        --environment $(AZURE_CONTAINER_ENV) \
	        --image $(AZURE_ACR_NAME).azurecr.io/static-site-builder:latest \
	        --registry-server $(AZURE_ACR_NAME).azurecr.io \
	        --registry-username $(AZURE_ACR_NAME) \
	        --registry-password \$$ACR_PASSWORD \
	        --target-port 3200 \
	        --ingress internal \
	        --min-replicas 1"

# マネージドIDのContainer Appへの割り当て
azure-assign-managed-identity:
	$(call read-env)
	docker run -it --rm -v $(HOME)/.azure:/root/.azure mcr.microsoft.com/azure-cli /bin/bash -c "\
	    echo '>>> API Container App にシステム割り当てマネージド ID を追加中...' && \
	    az containerapp identity assign --name api --resource-group $(AZURE_RESOURCE_GROUP) --system-assigned && \
	    echo 'Managed identity assigned.'"

# Container AppのマネージドIDへのストレージアクセス権の割り当て
azure-assign-storage-access:
	$(call read-env)
	@echo ">>> 現在のサブスクリプションIDを取得中..."
	$(eval AZURE_SUBSCRIPTION_ID := $(shell docker run --rm -v $(HOME)/.azure:/root/.azure mcr.microsoft.com/azure-cli az account show --query id -o tsv))
	@echo ">>> AZURE_SUBSCRIPTION_ID=$(AZURE_SUBSCRIPTION_ID)"
	@echo ">>> Container Apps のマネージド ID へのストレージアクセス権を割り当て中..."
	docker run -it --rm -v $(HOME)/.azure:/root/.azure mcr.microsoft.com/azure-cli /bin/bash -c "\
	    API_PRINCIPAL=\$$(az containerapp show --name api --resource-group $(AZURE_RESOURCE_GROUP) --query identity.principalId -o tsv); \
	    echo 'API container managed identity: '\$$API_PRINCIPAL; \
	    az role assignment create --assignee \$$API_PRINCIPAL \
	        --role 'Storage Blob Data Contributor' \
	        --scope '/subscriptions/$(AZURE_SUBSCRIPTION_ID)/resourceGroups/$(AZURE_RESOURCE_GROUP)/providers/Microsoft.Storage/storageAccounts/$(AZURE_BLOB_STORAGE_ACCOUNT_NAME)'; \
	    echo 'Storage access role assigned to API container.'"
	$(MAKE) azure-restart-api

# 環境変数の更新
azure-config-update:
	$(call read-env)
	docker run -it --rm -v $(shell pwd):/workspace -v $(HOME)/.azure:/root/.azure -w /workspace mcr.microsoft.com/azure-cli /bin/bash -c "\
	    API_DOMAIN=\$$(az containerapp show --name api --resource-group $(AZURE_RESOURCE_GROUP) --query properties.configuration.ingress.fqdn -o tsv) && \
	    PUBLIC_VIEWER_DOMAIN=\$$(az containerapp show --name public-viewer --resource-group $(AZURE_RESOURCE_GROUP) --query properties.configuration.ingress.fqdn -o tsv) && \
	    ADMIN_DOMAIN=\$$(az containerapp show --name admin --resource-group $(AZURE_RESOURCE_GROUP) --query properties.configuration.ingress.fqdn -o tsv) && \
	    STATIC_SITE_BUILDER_DOMAIN=\$$(az containerapp show --name static-site-builder --resource-group $(AZURE_RESOURCE_GROUP) --query properties.configuration.ingress.fqdn -o tsv) && \
	    echo '>>> ドメイン情報: API='\$$API_DOMAIN', PUBLIC_VIEWER='\$$PUBLIC_VIEWER_DOMAIN', ADMIN='\$$ADMIN_DOMAIN', STATIC_SITE_BUILDER='\$$STATIC_SITE_BUILDER_DOMAIN && \
	    echo '>>> APIの環境変数を更新...' && \
	    az containerapp update --name api --resource-group $(AZURE_RESOURCE_GROUP) \
	        --set-env-vars 'OPENAI_API_KEY=$(OPENAI_API_KEY)' 'PUBLIC_API_KEY=$(PUBLIC_API_KEY)' 'ADMIN_API_KEY=$(ADMIN_API_KEY)' 'LOG_LEVEL=info' 'AZURE_BLOB_STORAGE_ACCOUNT_NAME=$(AZURE_BLOB_STORAGE_ACCOUNT_NAME)' 'AZURE_BLOB_STORAGE_CONTAINER_NAME=$(AZURE_BLOB_STORAGE_CONTAINER_NAME)' 'STORAGE_TYPE=azure_blob' \"REVALIDATE_URL=https://\$$PUBLIC_VIEWER_DOMAIN/api/revalidate\" 'REVALIDATE_SECRET=$(REVALIDATE_SECRET)' && \
	    echo '>>> 公開閲覧用の環境変数を更新...' && \
	    az containerapp update --name public-viewer --resource-group $(AZURE_RESOURCE_GROUP) \
	        --set-env-vars 'NEXT_PUBLIC_PUBLIC_API_KEY=$(PUBLIC_API_KEY)' \"NEXT_PUBLIC_API_BASEPATH=https://\$$API_DOMAIN\" \"API_BASEPATH=https://\$$API_DOMAIN\" && \
	    echo '>>> 管理画面の環境変数を更新...' && \
	    az containerapp update --name admin --resource-group $(AZURE_RESOURCE_GROUP) \
	        --set-env-vars 'NEXT_PUBLIC_ADMIN_API_KEY=$(ADMIN_API_KEY)' \"NEXT_PUBLIC_CLIENT_BASEPATH=https://\$$PUBLIC_VIEWER_DOMAIN\" \"NEXT_PUBLIC_API_BASEPATH=https://\$$API_DOMAIN\" \"API_BASEPATH=https://\$$API_DOMAIN\" \"CLIENT_STATIC_BUILD_BASEPATH=https://\$$STATIC_SITE_BUILDER_DOMAIN\" 'BASIC_AUTH_USERNAME=$(BASIC_AUTH_USERNAME)' 'BASIC_AUTH_PASSWORD=$(BASIC_AUTH_PASSWORD)' && \
	    echo '>>> 静的サイトビルダーの環境変数を更新...' && \
	    az containerapp update --name static-site-builder --resource-group $(AZURE_RESOURCE_GROUP) \
	        --set-env-vars 'NEXT_PUBLIC_PUBLIC_API_KEY=$(PUBLIC_API_KEY)' \"NEXT_PUBLIC_API_BASEPATH=https://\$$API_DOMAIN\" \"API_BASEPATH=https://\$$API_DOMAIN\""

# adminアプリの環境変数を修正してビルド
azure-fix-admin:
	$(call read-env)
	@echo ">>> API・公開閲覧用・静的サイトビルダーのドメイン情報を取得しています..."
	$(eval API_DOMAIN=$(shell docker run --rm -v $(HOME)/.azure:/root/.azure mcr.microsoft.com/azure-cli /bin/bash -c "az containerapp show --name api --resource-group $(AZURE_RESOURCE_GROUP) --query properties.configuration.ingress.fqdn -o tsv 2>/dev/null | tail -n 1"))
	$(eval PUBLIC_VIEWER_DOMAIN=$(shell docker run --rm -v $(HOME)/.azure:/root/.azure mcr.microsoft.com/azure-cli /bin/bash -c "az containerapp show --name public-viewer --resource-group $(AZURE_RESOURCE_GROUP) --query properties.configuration.ingress.fqdn -o tsv 2>/dev/null | tail -n 1"))
	$(eval STATIC_SITE_BUILDER_DOMAIN=$(shell docker run --rm -v $(HOME)/.azure:/root/.azure mcr.microsoft.com/azure-cli /bin/bash -c "az containerapp show --name static-site-builder --resource-group $(AZURE_RESOURCE_GROUP) --query properties.configuration.ingress.fqdn -o tsv 2>/dev/null | tail -n 1"))

	@echo ">>> API_DOMAIN=$(API_DOMAIN)"
	@echo ">>> PUBLIC_VIEWER_DOMAIN=$(PUBLIC_VIEWER_DOMAIN)"
	@echo ">>> STATIC_SITE_BUILDER_DOMAIN=$(STATIC_SITE_BUILDER_DOMAIN)"

	@echo ">>> 環境変数を設定し、キャッシュを無効化してadminを再ビルド..."
	docker build --platform linux/amd64 --no-cache \
	  --build-arg NEXT_PUBLIC_API_BASEPATH=https://$(API_DOMAIN) \
	  --build-arg NEXT_PUBLIC_ADMIN_API_KEY=$(ADMIN_API_KEY) \
	  --build-arg NEXT_PUBLIC_CLIENT_BASEPATH=https://$(PUBLIC_VIEWER_DOMAIN) \
	  --build-arg CLIENT_STATIC_BUILD_BASEPATH=https://$(STATIC_SITE_BUILDER_DOMAIN) \
	  -t $(AZURE_ACR_NAME).azurecr.io/admin:latest ./apps/admin

	@echo ">>> イメージをプッシュ..."
	docker push $(AZURE_ACR_NAME).azurecr.io/admin:latest

	@echo ">>> コンテナアプリを更新..."
	docker run --rm -v $(HOME)/.azure:/root/.azure mcr.microsoft.com/azure-cli /bin/bash -c "\
	  az containerapp update --name admin --resource-group $(AZURE_RESOURCE_GROUP) \
	    --image $(AZURE_ACR_NAME).azurecr.io/admin:latest"

	@$(MAKE) azure-restart-admin

# 環境の検証
azure-verify:
	$(call read-env)
	@echo ">>> 環境の検証を開始..."
	@docker run --rm -v $(HOME)/.azure:/root/.azure mcr.microsoft.com/azure-cli /bin/bash -c "\
	  API_UP=\$$(az containerapp show --name api --resource-group $(AZURE_RESOURCE_GROUP) --query 'properties.latestRevisionName' -o tsv); \
	  PUBLIC_VIEWER_UP=\$$(az containerapp show --name public-viewer --resource-group $(AZURE_RESOURCE_GROUP) --query 'properties.latestRevisionName' -o tsv); \
	  ADMIN_UP=\$$(az containerapp show --name admin --resource-group $(AZURE_RESOURCE_GROUP) --query 'properties.latestRevisionName' -o tsv); \
	  STATIC_SITE_BUILDER_UP=\$$(az containerapp show --name static-site-builder --resource-group $(AZURE_RESOURCE_GROUP) --query 'properties.latestRevisionName' -o tsv); \
	  echo '検証結果:'; \
	  echo 'API Status: '\$$API_UP; \
	  echo 'Public Viewer Status: '\$$PUBLIC_VIEWER_UP; \
	  echo 'Admin Status: '\$$ADMIN_UP; \
	  echo 'Static Site Builder Status: '\$$STATIC_SITE_BUILDER_UP; \
	  if [ -z \"\$$API_UP\" ] || [ -z \"\$$PUBLIC_VIEWER_UP\" ] || [ -z \"\$$ADMIN_UP\" ]; then \
	    echo '警告: いくつかのサービスが正しくデプロイされていません。'; \
	  else \
	    echo 'すべてのサービスが正常にデプロイされています。'; \
	  fi \
	"

# サービスURLの取得
azure-info:
	$(call read-env)
	@echo "----------------------------------------------------------------------------------------"
	$(eval API_DOMAIN=$(shell docker run --rm -v $(HOME)/.azure:/root/.azure mcr.microsoft.com/azure-cli /bin/bash -c "az containerapp show --name api --resource-group $(AZURE_RESOURCE_GROUP) --query properties.configuration.ingress.fqdn -o tsv 2>/dev/null | tail -n 1"))
	$(eval PUBLIC_VIEWER_DOMAIN=$(shell docker run --rm -v $(HOME)/.azure:/root/.azure mcr.microsoft.com/azure-cli /bin/bash -c "az containerapp show --name public-viewer --resource-group $(AZURE_RESOURCE_GROUP) --query properties.configuration.ingress.fqdn -o tsv 2>/dev/null | tail -n 1"))
	$(eval ADMIN_DOMAIN=$(shell docker run --rm -v $(HOME)/.azure:/root/.azure mcr.microsoft.com/azure-cli /bin/bash -c "az containerapp show --name admin --resource-group $(AZURE_RESOURCE_GROUP) --query properties.configuration.ingress.fqdn -o tsv 2>/dev/null | tail -n 1"))
	@echo "public-viewer: https://$(PUBLIC_VIEWER_DOMAIN)"
	@echo "admin        : https://$(ADMIN_DOMAIN)"
	@echo "API          : https://$(API_DOMAIN)"
	@echo "----------------------------------------------------------------------------------------"

# 完全セットアップを一括実行
azure-setup-all:
	$(call read-env)
	@echo ">>> 1. リソースグループとACRのセットアップ..."
	@$(MAKE) azure-setup

	@echo ">>> 2. ACRへのログイン..."
	@$(MAKE) azure-acr-login-auto


	@echo ">>> 3. ストレージの作成"
	@$(MAKE) azure-create-storage

	@echo ">>> 4. コンテナイメージのビルド..."
	@$(MAKE) azure-build

	@echo ">>> 5. イメージのプッシュ..."
	@$(MAKE) azure-push

	@echo ">>> 6. Container Appsへのデプロイ..."
	@$(MAKE) azure-deploy

	@echo ">>> コンテナアプリ作成を待機中（40秒）..."
	@sleep 40

	@echo ">>> 7. マネージドIDのContainer Appへの割り当て"
	@$(MAKE) azure-assign-managed-identity

	@echo ">>> 8. Container AppのマネージドIDへのストレージアクセス権の割り当て"
	@$(MAKE) azure-assign-storage-access

	@echo ">>> 8a. ポリシーとヘルスチェックの適用..."
	@$(MAKE) azure-apply-policies

	@echo ">>> 9. 環境変数の設定..."
	@$(MAKE) azure-config-update

	@echo ">>> 10. 環境変数の反映を待機中（30秒）..."
	@sleep 30

	@echo ">>> 11. 管理画面の環境変数を修正してビルド..."
	@$(MAKE) azure-fix-admin

	@echo ">>> 12. 環境の検証..."
	@$(MAKE) azure-verify

	@echo ">>> 13. サービスURLの確認..."
	@$(MAKE) azure-info

	@echo ">>> セットアップが完了しました。上記のURLでサービスにアクセスできます。"

# セットアップ後に生成された環境変数を保存
azure-save-env:
	@if [ -f .env.azure.generated ]; then \
	    if [ -f .env.azure ]; then \
	        echo ">>> .env.azureファイルがすでに存在します。.env.azure.generatedの内容を追加します。"; \
	        cat .env.azure.generated >> .env.azure; \
	    else \
	        echo ">>> .env.azureファイルを生成します。"; \
	        cp .env.azure.example .env.azure; \
	        cat .env.azure.generated >> .env.azure; \
	    fi; \
	    echo ">>> 自動生成された環境変数を.env.azureに保存しました"; \
	    rm .env.azure.generated; \
	fi

##############################################################################
# Azure運用時コマンド
##############################################################################

# コンテナをスケールダウン（料金発生を抑制）
azure-stop:
	$(call read-env)
	docker run -it --rm -v $(HOME)/.azure:/root/.azure mcr.microsoft.com/azure-cli /bin/bash -c "\
	    echo '>>> APIコンテナをスケールダウン中...' && \
	    az containerapp update --name api --resource-group $(AZURE_RESOURCE_GROUP) --min-replicas 0 && \
	    echo '>>> 公開閲覧用コンテナをスケールダウン中...' && \
	    az containerapp update --name public-viewer --resource-group $(AZURE_RESOURCE_GROUP) --min-replicas 0 && \
	    echo '>>> 管理画面コンテナをスケールダウン中...' && \
	    az containerapp update --name admin --resource-group $(AZURE_RESOURCE_GROUP) --min-replicas 0 && \
	    echo '>>> 静的サイトビルダーコンテナをスケールダウン中...' && \
	    az containerapp update --name static-site-builder --resource-group $(AZURE_RESOURCE_GROUP) --min-replicas 0 && \
	    echo '>>> すべてのコンテナのスケールダウンが完了しました。'"

# コンテナを再起動（使用時）
azure-start:
	$(call read-env)
	docker run -it --rm -v $(HOME)/.azure:/root/.azure mcr.microsoft.com/azure-cli /bin/bash -c "\
	    echo '>>> APIコンテナを起動中...' && \
	    az containerapp update --name api --resource-group $(AZURE_RESOURCE_GROUP) --min-replicas 1 && \
	    echo '>>> 公開閲覧用コンテナを起動中...' && \
	    az containerapp update --name public-viewer --resource-group $(AZURE_RESOURCE_GROUP) --min-replicas 1 && \
	    echo '>>> 管理画面コンテナを起動中...' && \
	    az containerapp update --name admin --resource-group $(AZURE_RESOURCE_GROUP) --min-replicas 1 && \
	    echo '>>> 静的サイトビルダーコンテナを起動中...' && \
	    az containerapp update --name static-site-builder --resource-group $(AZURE_RESOURCE_GROUP) --min-replicas 1 && \
	    echo '>>> すべてのコンテナの起動が完了しました。'"

# コンテナのステータス確認
azure-status:
	$(call read-env)
	docker run -it --rm -v $(HOME)/.azure:/root/.azure mcr.microsoft.com/azure-cli /bin/bash -c "\
	    echo '>>> APIコンテナのステータス:' && \
	    az containerapp revision list --name api --resource-group $(AZURE_RESOURCE_GROUP) -o table && \
	    echo '>>> 公開閲覧用コンテナのステータス:' && \
	    az containerapp revision list --name public-viewer --resource-group $(AZURE_RESOURCE_GROUP) -o table && \
	    echo '>>> 管理画面コンテナのステータス:' && \
	    az containerapp revision list --name admin --resource-group $(AZURE_RESOURCE_GROUP) -o table && \
	    echo '>>> 静的サイトビルダーコンテナのステータス:' && \
	    az containerapp revision list --name static-site-builder --resource-group $(AZURE_RESOURCE_GROUP) -o table"

# コンテナのログ確認
azure-logs-public-viewer:
	$(call read-env)
	docker run -it --rm -v $(HOME)/.azure:/root/.azure mcr.microsoft.com/azure-cli az containerapp logs show --name public-viewer --resource-group $(AZURE_RESOURCE_GROUP) --follow

azure-logs-api:
	$(call read-env)
	docker run -it --rm -v $(HOME)/.azure:/root/.azure mcr.microsoft.com/azure-cli az containerapp logs show --name api --resource-group $(AZURE_RESOURCE_GROUP) --follow

azure-logs-admin:
	$(call read-env)
	docker run -it --rm -v $(HOME)/.azure:/root/.azure mcr.microsoft.com/azure-cli az containerapp logs show --name admin --resource-group $(AZURE_RESOURCE_GROUP) --follow

azure-logs-static-site-builder:
	$(call read-env)
	docker run -it --rm -v $(HOME)/.azure:/root/.azure mcr.microsoft.com/azure-cli az containerapp logs show --name static-site-builder --resource-group $(AZURE_RESOURCE_GROUP) --follow

# REVALIDATE_SECRETが.envファイルに定義されているか確認
azure-check-revalidate-secret:
	$(call read-env)
	@if [ -z "$(REVALIDATE_SECRET)" ]; then \
		echo "エラー: REVALIDATE_SECRETが.envファイルに定義されていません。"; \
		echo "REVALIDATE_SECRETを.envファイルに追加してから再実行してください。"; \
		exit 1; \
	fi

# デプロイの完全アップデート
azure-update-deployment:
	$(call read-env)
	@$(MAKE) azure-check-revalidate-secret

	@echo ">>> コンテナイメージのビルド..."
	@$(MAKE) azure-build

	@echo ">>> イメージのプッシュ..."
	@$(MAKE) azure-acr-login-auto
	@$(MAKE) azure-push

	@echo ">>> 環境変数の設定..."
	@$(MAKE) azure-config-update

	@echo ">>> コンテナ再起動..."
	@$(MAKE) azure-restart-api
	@$(MAKE) azure-restart-public-viewer
	@$(MAKE) azure-restart-static-site-builder
	@echo ">>> 管理画面コンテナを環境変数を修正して再起動中..."
	@$(MAKE) azure-fix-admin

	@echo ">>> 9. サービスURLの確認..."
	@$(MAKE) azure-info

	@echo ">>> デプロイの更新が完了しました。"

# apiを再起動（ストレージへのアクセス権限を割り当てた後、api上にストレージの情報をsyncするために利用）
# azure-update-deployment時にイメージのpush後にも必要
azure-restart-api:
	$(call read-env)
	@echo ">>> API Container App をスケールダウン（再起動準備）..."
	docker run --rm -v $(HOME)/.azure:/root/.azure mcr.microsoft.com/azure-cli \
	az containerapp update --name api --resource-group $(AZURE_RESOURCE_GROUP) --min-replicas 0
	@sleep 5
	@echo ">>> API Container App をスケールアップ（再起動）..."
	docker run --rm -v $(HOME)/.azure:/root/.azure mcr.microsoft.com/azure-cli \
	az containerapp update --name api --resource-group $(AZURE_RESOURCE_GROUP) --min-replicas 1

# azure-update-deployment時にイメージのpush後に必要
azure-restart-public-viewer:
	$(call read-env)
	@echo ">>> 公開閲覧用コンテナを再起動中..."
	@docker run --rm -v $(HOME)/.azure:/root/.azure mcr.microsoft.com/azure-cli /bin/bash -c "\
	  echo '>>> 一時的にスケールダウン...' && \
	  az containerapp update --name public-viewer --resource-group $(AZURE_RESOURCE_GROUP) --min-replicas 0 && \
	  echo '>>> 再度スケールアップ...' && \
	  sleep 5 && \
	  az containerapp update --name public-viewer --resource-group $(AZURE_RESOURCE_GROUP) --min-replicas 1"

# azure-update-deployment時にイメージのpush後にも必要
azure-restart-admin:
	$(call read-env)
	@echo ">>> 管理画面コンテナを再起動（スケールダウン後にスケールアップ）..."
	docker run --rm -v $(HOME)/.azure:/root/.azure mcr.microsoft.com/azure-cli /bin/bash -c "\
	  echo '>>> 一時的にスケールダウン...' && \
	  az containerapp update --name admin --resource-group $(AZURE_RESOURCE_GROUP) --min-replicas 0 && \
	  echo '>>> 再度スケールアップ...' && \
	  sleep 5 && \
	  az containerapp update --name admin --resource-group $(AZURE_RESOURCE_GROUP) --min-replicas 1"

# azure-update-deployment時にイメージのpush後にも必要
azure-restart-static-site-builder:
	$(call read-env)
	@echo ">>> 静的サイトビルダーコンテナを再起動（スケールダウン後にスケールアップ）..."
	docker run --rm -v $(HOME)/.azure:/root/.azure mcr.microsoft.com/azure-cli /bin/bash -c "\
	  echo '>>> 一時的にスケールダウン...' && \
	  az containerapp update --name static-site-builder --resource-group $(AZURE_RESOURCE_GROUP) --min-replicas 0 && \
	  echo '>>> 再度スケールアップ...' && \
	  sleep 5 && \
	  az containerapp update --name static-site-builder --resource-group $(AZURE_RESOURCE_GROUP) --min-replicas 1"

# リソースの完全削除
azure-cleanup:
	$(call read-env)
	@echo "警告: この操作はリソースグループ $(AZURE_RESOURCE_GROUP) を完全に削除します。"
	@echo "この操作は元に戻せません。すべてのサービスやデータが失われます。"
	@read -p "本当に削除しますか？ [y/N]: " confirm; \
	if [ "$$confirm" != "y" ] && [ "$$confirm" != "Y" ]; then \
	    echo "操作をキャンセルしました。"; \
	    exit 1; \
	fi
	docker run -it --rm -v $(HOME)/.azure:/root/.azure mcr.microsoft.com/azure-cli az group delete --name $(AZURE_RESOURCE_GROUP) --yes

# ヘルスチェック設定とイメージプルポリシーの適用
azure-apply-policies:
	$(call read-env)
	@echo ">>> YAMLテンプレートから設定ファイルを生成..."
	@$(MAKE) prepare-yaml
	@echo ">>> すべてのコンテナにポリシーを適用します..."
	@docker run --rm -v $(shell pwd):/workspace -v $(HOME)/.azure:/root/.azure -w /workspace mcr.microsoft.com/azure-cli /bin/bash -c "\
	    echo '>>> APIコンテナにヘルスチェック設定とイメージプルポリシーを適用...' && \
	    az containerapp update --name api --resource-group $(AZURE_RESOURCE_GROUP) \
	        --yaml /workspace/.azure/generated/policies/api-pull-policy.yaml || echo '警告: APIポリシー適用に失敗しました' && \
	    az containerapp update --name api --resource-group $(AZURE_RESOURCE_GROUP) \
	        --yaml /workspace/.azure/generated/health/api-health-probe.yaml || echo '警告: APIヘルスプローブ適用に失敗しました' && \
	    echo '>>> 公開閲覧用コンテナにヘルスチェック設定とイメージプルポリシーを適用...' && \
	    az containerapp update --name public-viewer --resource-group $(AZURE_RESOURCE_GROUP) \
	        --yaml /workspace/.azure/generated/policies/public-viewer-pull-policy.yaml || echo '警告: 公開閲覧用ポリシー適用に失敗しました' && \
	    az containerapp update --name public-viewer --resource-group $(AZURE_RESOURCE_GROUP) \
	        --yaml /workspace/.azure/generated/health/public-viewer-health-probe.yaml || echo '警告: 公開閲覧用ヘルスプローブ適用に失敗しました' && \
	    echo '>>> 管理画面コンテナにヘルスチェック設定とイメージプルポリシーを適用...' && \
	    az containerapp update --name admin --resource-group $(AZURE_RESOURCE_GROUP) \
	        --yaml /workspace/.azure/generated/policies/admin-pull-policy.yaml || echo '警告: 管理画面ポリシー適用に失敗しました' && \
	    az containerapp update --name admin --resource-group $(AZURE_RESOURCE_GROUP) \
	        --yaml /workspace/.azure/generated/health/admin-health-probe.yaml || echo '警告: 管理画面ヘルスプローブ適用に失敗しました' && \
	    echo '>>> 静的サイトビルダーコンテナにヘルスチェック設定とイメージプルポリシーを適用...' && \
	    az containerapp update --name static-site-builder --resource-group $(AZURE_RESOURCE_GROUP) \
	        --yaml /workspace/.azure/generated/policies/static-site-builder-pull-policy.yaml || echo '警告: 静的サイトビルダーポリシー適用に失敗しました' && \
	    az containerapp update --name static-site-builder --resource-group $(AZURE_RESOURCE_GROUP) \
	        --yaml /workspace/.azure/generated/health/static-site-builder-health-probe.yaml || echo '警告: 静的サイトビルダーヘルスプローブ適用に失敗しました'"

# YAMLテンプレートを処理
prepare-yaml:
	$(call read-env)
	@echo ">>> YAMLテンプレートを処理中..."
	@mkdir -p .azure/generated/policies
	@mkdir -p .azure/generated/health
	@for file in .azure/templates/policies/*.yaml; do \
	    outfile=$$(basename $$file); \
	    echo ">>> 処理中: $$file -> .azure/generated/policies/$$outfile"; \
	    cat $$file | \
	    sed "s/{{AZURE_ACR_NAME}}/$(AZURE_ACR_NAME)/g" | \
	    sed "s/{{AZURE_RESOURCE_GROUP}}/$(AZURE_RESOURCE_GROUP)/g" | \
	    sed "s/{{AZURE_CONTAINER_ENV}}/$(AZURE_CONTAINER_ENV)/g" | \
	    sed "s/{{AZURE_LOCATION}}/$(AZURE_LOCATION)/g" > .azure/generated/policies/$$outfile; \
	done
	@for file in .azure/templates/health/*.yaml; do \
	    outfile=$$(basename $$file); \
	    echo ">>> 処理中: $$file -> .azure/generated/health/$$outfile"; \
	    cat $$file | \
	    sed "s/{{AZURE_ACR_NAME}}/$(AZURE_ACR_NAME)/g" | \
	    sed "s/{{AZURE_RESOURCE_GROUP}}/$(AZURE_RESOURCE_GROUP)/g" | \
	    sed "s/{{AZURE_CONTAINER_ENV}}/$(AZURE_CONTAINER_ENV)/g" | \
	    sed "s/{{AZURE_LOCATION}}/$(AZURE_LOCATION)/g" > .azure/generated/health/$$outfile; \
	done
