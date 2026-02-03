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
  const dummyServerUrl =
    process.env.NEXT_PUBLIC_API_BASEPATH ?? process.env.API_BASEPATH ?? "http://localhost:8002";

  const isServerReady = async (url: string) => {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 1000);
    try {
      const response = await fetch(url, { cache: "no-store", signal: controller.signal });
      return response.status < 500;
    } catch {
      return false;
    } finally {
      clearTimeout(timeoutId);
    }
  };

  const waitForServer = async (url: string, timeoutMs = 20000) => {
    const start = Date.now();
    while (Date.now() - start < timeoutMs) {
      if (await isServerReady(url)) return true;
      await new Promise((resolve) => setTimeout(resolve, 500));
    }
    return false;
  };

  try {
    console.log(">>> 静的ビルドを生成中...");
    console.log(">>> これには数分かかる場合があります...");

    // ダミーAPIサーバーは Playwright の webServer で起動される前提
    console.log(">>> ダミーAPIサーバー（port 8002）が起動していることを確認します");
    const ready = await waitForServer(dummyServerUrl, 20000);
    if (!ready) {
      throw new Error("Dummy server is not ready for static build");
    }

    // Subdirectory ホスティング用の静的ビルドを生成（先に実行）
    console.log(">>> 1/2: Subdirectory ホスティング用のビルドを生成中...");
    execSync(`${buildScript} subdir`, {
      stdio: "inherit",
      env: {
        ...process.env,
        NEXT_PUBLIC_API_BASEPATH: dummyServerUrl,
        API_BASEPATH: dummyServerUrl,
        NEXT_PUBLIC_PUBLIC_API_KEY: "public",
      },
    });

    // Root ホスティング用の静的ビルドを生成（後に実行してout/に配置）
    console.log(">>> 2/2: Root ホスティング用のビルドを生成中...");
    execSync(`${buildScript} root`, {
      stdio: "inherit",
      env: {
        ...process.env,
        NEXT_PUBLIC_API_BASEPATH: dummyServerUrl,
        API_BASEPATH: dummyServerUrl,
        NEXT_PUBLIC_PUBLIC_API_KEY: "public",
      },
    });

    console.log(">>> 静的ビルド完了（root: apps/public-viewer/out, subdir: apps/public-viewer/out-subdir）");
  } catch (error) {
    console.error(">>> 静的ビルドに失敗しました:", error);
    throw error;
  } finally {
    // dummy-server lifecycle is managed by Playwright webServer
  }

  console.log(">>> グローバルセットアップ完了");
}
