import { NextResponse } from "next/server";

export async function GET(request: Request) {
  const requestApiKey = request.headers.get("x-api-key");
  const validApiKey = process.env.PUBLIC_API_KEY;

  if (!requestApiKey || requestApiKey !== validApiKey) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  // E2E_TEST環境変数が設定されている場合はテストフィクスチャを使用
  if (process.env.E2E_TEST === "true") {
    // 管理画面用の空のレポートリストを返す
    return NextResponse.json([]);
  }

  // 通常のダミーデータ
  return NextResponse.json([
    {
      id: "example",
      slug: "example",
      status: "ready",
      title: "[テスト]人類が人工知能を開発・展開する上で、最優先すべき課題は何でしょうか？",
      createdAt: new Date().toISOString(),
    },
  ]);
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
