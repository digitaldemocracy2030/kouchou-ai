import { execSync } from "node:child_process";
import * as path from "node:path";

/**
 * Playwright グローバルセットアップ
 * テスト実行前に静的ビルドを生成します
 */
export default async function globalSetup() {
  console.log(">>> グローバルセットアップ開始");

  // 静的ビルドを生成するかどうかを環境変数で制御
  const skipBuild = process.env.SKIP_STATIC_BUILD === "true";

  if (skipBuild) {
    console.log(">>> SKIP_STATIC_BUILD=true のため、静的ビルドをスキップします");
    return;
  }

  const scriptDir = __dirname;
  const buildScript = path.join(scriptDir, "build-static.sh");

  try {
    console.log(">>> 静的ビルドを生成中...");
    console.log(">>> これには数分かかる場合があります...");

    // ダミーAPIサーバーが起動していることを確認
    console.log(">>> ダミーAPIサーバー（port 8002）が起動していることを確認してください");

    // Subdirectory ホスティング用の静的ビルドを生成（先に実行）
    console.log(">>> 1/2: Subdirectory ホスティング用のビルドを生成中...");
    execSync(`${buildScript} subdir`, {
      stdio: "inherit",
      env: {
        ...process.env,
        NEXT_PUBLIC_API_BASEPATH: "http://localhost:8002",
        API_BASEPATH: "http://localhost:8002",
        NEXT_PUBLIC_PUBLIC_API_KEY: "public",
      },
    });

    // Root ホスティング用の静的ビルドを生成（後に実行してout/に配置）
    console.log(">>> 2/2: Root ホスティング用のビルドを生成中...");
    execSync(`${buildScript} root`, {
      stdio: "inherit",
      env: {
        ...process.env,
        NEXT_PUBLIC_API_BASEPATH: "http://localhost:8002",
        API_BASEPATH: "http://localhost:8002",
        NEXT_PUBLIC_PUBLIC_API_KEY: "public",
      },
    });

    console.log(">>> 静的ビルド完了（root: client/out, subdir: client/out-subdir）");
  } catch (error) {
    console.error(">>> 静的ビルドに失敗しました:", error);
    throw error;
  }

  console.log(">>> グローバルセットアップ完了");
}
