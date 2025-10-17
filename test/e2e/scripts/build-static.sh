#!/bin/bash

# 静的ビルドを生成するスクリプト
# 使用方法: ./scripts/build-static.sh [root|subdir]

set -e

BUILD_TYPE=${1:-root}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLIENT_DIR="$SCRIPT_DIR/../../../client"

echo ">>> 静的ビルドを生成中: $BUILD_TYPE"
echo ">>> SCRIPT_DIR: $SCRIPT_DIR"
echo ">>> CLIENT_DIR: $CLIENT_DIR"

if [ ! -d "$CLIENT_DIR" ]; then
  echo "エラー: clientディレクトリが見つかりません: $CLIENT_DIR"
  exit 1
fi

cd "$CLIENT_DIR" || exit 1
echo ">>> 現在のディレクトリ: $(pwd)"

if [ "$BUILD_TYPE" = "root" ]; then
  # 既存のoutディレクトリを削除
  if [ -d "out" ]; then
    echo ">>> 既存のoutディレクトリを削除中..."
    rm -rf out
  fi

  echo ">>> Root ホスティング用のビルドを実行中..."
  NEXT_PUBLIC_API_BASEPATH=http://localhost:8002 \
  API_BASEPATH=http://localhost:8002 \
  NEXT_PUBLIC_PUBLIC_API_KEY=public \
  NEXT_PUBLIC_STATIC_EXPORT_BASE_PATH="" \
  npm run build:static

  echo ">>> 静的ビルド完了: client/out"

elif [ "$BUILD_TYPE" = "subdir" ]; then
  # 既存のout-subdirディレクトリを削除
  if [ -d "out-subdir" ]; then
    echo ">>> 既存のout-subdirディレクトリを削除中..."
    rm -rf out-subdir
  fi

  echo ">>> Subdirectory ホスティング用のビルドを実行中..."
  NEXT_PUBLIC_API_BASEPATH=http://localhost:8002 \
  API_BASEPATH=http://localhost:8002 \
  NEXT_PUBLIC_PUBLIC_API_KEY=public \
  NEXT_PUBLIC_STATIC_EXPORT_BASE_PATH="/kouchou-ai" \
  npm run build:static

  # ビルド結果をout-subdirに移動
  if [ -d "out" ]; then
    echo ">>> ビルド結果をout-subdirに移動中..."
    mv out out-subdir
  fi

  echo ">>> 静的ビルド完了: client/out-subdir"

else
  echo "エラー: 無効なビルドタイプ: $BUILD_TYPE"
  echo "使用方法: ./scripts/build-static.sh [root|subdir]"
  exit 1
fi
