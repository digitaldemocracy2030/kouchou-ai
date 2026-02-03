import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { NextResponse } from "next/server";

export async function GET(request: Request) {
  const requestApiKey = request.headers.get("x-api-key");
  const validApiKey = process.env.ADMIN_API_KEY;
  const corsHeaders = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, x-api-key",
  };

  if (!requestApiKey || requestApiKey !== validApiKey) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401, headers: corsHeaders });
  }

  // E2E_TEST環境変数が設定されている場合はテストフィクスチャを使用
  if (process.env.E2E_TEST === "true") {
    const fixturePath = resolve(process.cwd(), "../../test/e2e/fixtures/client/reports.json");
    const fixtureJson = await readFile(fixturePath, "utf-8");
    const reports = JSON.parse(fixtureJson);
    return NextResponse.json(reports, { headers: corsHeaders });
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
  ], { headers: corsHeaders });
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
