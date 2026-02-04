#!/bin/bash

# 静的ビルドを生成するスクリプト
# 使用方法: ./scripts/build-static.sh [root|subdir]

set -e

BUILD_TYPE=${1:-root}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PUBLIC_VIEWER_DIR="$SCRIPT_DIR/../../../apps/public-viewer"

echo ">>> 静的ビルドを生成中: $BUILD_TYPE"
echo ">>> SCRIPT_DIR: $SCRIPT_DIR"
echo ">>> PUBLIC_VIEWER_DIR: $PUBLIC_VIEWER_DIR"

if [ ! -d "$PUBLIC_VIEWER_DIR" ]; then
  echo "エラー: public-viewerディレクトリが見つかりません: $PUBLIC_VIEWER_DIR"
  exit 1
fi

cd "$PUBLIC_VIEWER_DIR" || exit 1
echo ">>> 現在のディレクトリ: $(pwd)"

if [ "$BUILD_TYPE" = "root" ]; then
  # 既存のout-rootディレクトリを削除
  if [ -d "out-root" ]; then
    echo ">>> 既存のout-rootディレクトリを削除中..."
    rm -rf out-root
  fi
  # 既存のoutディレクトリを削除
  if [ -d "out" ]; then
    echo ">>> 既存のoutディレクトリを削除中..."
    rm -rf out
  fi
  # 既存の.nextディレクトリを削除（basePath切り替え時のキャッシュを避ける）
  if [ -d ".next" ]; then
    echo ">>> 既存の.nextディレクトリを削除中..."
    rm -rf .next
  fi

  echo ">>> Root ホスティング用のビルドを実行中..."
  NEXT_PUBLIC_API_BASEPATH=http://localhost:8002 \
  API_BASEPATH=http://localhost:8002 \
  NEXT_PUBLIC_PUBLIC_API_KEY=public \
  NEXT_PUBLIC_STATIC_EXPORT_BASE_PATH="" \
  pnpm run build:static

  if [ ! -d "out" ]; then
    echo "エラー: out ディレクトリが生成されませんでした"
    exit 1
  fi
  echo ">>> ビルド結果をout-rootに移動中..."
  mv out out-root

  echo ">>> 静的ビルド完了: apps/public-viewer/out-root"

elif [ "$BUILD_TYPE" = "subdir" ]; then
  # 既存のout-subdirディレクトリを削除
  if [ -d "out-subdir" ]; then
    echo ">>> 既存のout-subdirディレクトリを削除中..."
    rm -rf out-subdir
  fi
  # 既存のoutディレクトリを削除
  if [ -d "out" ]; then
    echo ">>> 既存のoutディレクトリを削除中..."
    rm -rf out
  fi
  # 既存の.nextディレクトリを削除（basePath切り替え時のキャッシュを避ける）
  if [ -d ".next" ]; then
    echo ">>> 既存の.nextディレクトリを削除中..."
    rm -rf .next
  fi

  echo ">>> Subdirectory ホスティング用のビルドを実行中..."
  NEXT_PUBLIC_API_BASEPATH=http://localhost:8002 \
  API_BASEPATH=http://localhost:8002 \
  NEXT_PUBLIC_PUBLIC_API_KEY=public \
  NEXT_PUBLIC_STATIC_EXPORT_BASE_PATH="/kouchou-ai" \
  pnpm run build:static

  # ビルド結果をout-subdir/kouchou-aiに移動
  if [ ! -d "out" ]; then
    echo "エラー: out ディレクトリが生成されませんでした"
    exit 1
  fi
  echo ">>> ビルド結果をout-subdir/kouchou-aiに移動中..."
  mkdir -p out-subdir
  mv out out-subdir/kouchou-ai

  echo ">>> 静的ビルド完了: apps/public-viewer/out-subdir/kouchou-ai"

else
  echo "エラー: 無効なビルドタイプ: $BUILD_TYPE"
  echo "使用方法: ./scripts/build-static.sh [root|subdir]"
  exit 1
fi
