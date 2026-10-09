import fs from "node:fs/promises";
import path from "node:path";

export async function GET(request: Request) {
  const requestApiKey = request.headers.get("x-api-key");
  const validApiKey = process.env.PUBLIC_API_KEY;
  if (!requestApiKey || requestApiKey !== validApiKey) {
    return new Response(JSON.stringify({ error: "Unauthorized" }), {
      status: 401,
      headers: {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
      },
    });
  }

  // E2E_TEST環境変数が設定されている場合はテストフィクスチャを使用
  let data: unknown;
  if (process.env.E2E_TEST === "true") {
    try {
      const fixtureDir = path.resolve(process.cwd(), "../../test/e2e/fixtures/client");
      const fixturesPath = path.resolve(fixtureDir, "reports.json");
      const fileContent = await fs.readFile(fixturesPath, "utf8");
      data = JSON.parse(fileContent);
    } catch (error) {
      // フィクスチャ読み込み失敗時はフォールバック
      console.error("Failed to load test fixtures, using fallback data:", error);
      data = [];
    }
  } else {
    // 通常のダミーデータ
    data = [
      {
        slug: "example",
        status: "ready",
        title: "[テスト]人類が人工知能を開発・展開する上で、最優先すべき課題は何でしょうか？",
        description:
          "あのイーハトーヴォのすきとおった風、夏でも底に冷たさをもつ青いそら、うつくしい森で飾られたモリーオ市、郊外のぎらぎらひかる草の波。",
        isPubcom: true,
      },
    ];
  }

  return new Response(JSON.stringify(data), {
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*",
    },
  });
}

export async function OPTIONS() {
  return new Response(null, {
    headers: {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type, x-api-key",
    },
  });
}
