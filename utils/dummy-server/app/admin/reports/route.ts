import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { NextResponse } from "next/server";

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, x-api-key",
};

// Server Action が実際に送った本文を、テストごとに異なるレポートIDで参照する。
const submittedReports = new Map<string, unknown>();

function isAuthorized(request: Request) {
  const apiKey = request.headers.get("x-api-key");
  return Boolean(apiKey) && apiKey === process.env.ADMIN_API_KEY;
}

export async function GET(request: Request) {
  if (!isAuthorized(request)) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401, headers: corsHeaders });
  }

  // E2E_TEST環境変数が設定されている場合はテストフィクスチャを使用
  if (process.env.E2E_TEST === "true") {
    const submittedId = new URL(request.url).searchParams.get("e2eSubmittedId");
    if (submittedId !== null) {
      const report = submittedReports.get(submittedId);
      if (report === undefined) {
        return NextResponse.json({ error: "Not Found" }, { status: 404, headers: corsHeaders });
      }
      return NextResponse.json(report, {
        headers: { ...corsHeaders, "Cache-Control": "no-store" },
      });
    }
    const fixturePath = resolve(process.cwd(), "../../test/e2e/fixtures/client/reports.json");
    const fixtureJson = await readFile(fixturePath, "utf-8");
    const reports = JSON.parse(fixtureJson);
    return NextResponse.json(reports, { headers: corsHeaders });
  }

  // 通常のダミーデータ
  return NextResponse.json(
    [
      {
        id: "example",
        slug: "example",
        status: "ready",
        title: "[テスト]人類が人工知能を開発・展開する上で、最優先すべき課題は何でしょうか？",
        createdAt: new Date().toISOString(),
      },
    ],
    { headers: corsHeaders },
  );
}

export async function POST(request: Request) {
  if (!isAuthorized(request)) {
    return NextResponse.json({ detail: "Unauthorized" }, { status: 401, headers: corsHeaders });
  }
  if (process.env.E2E_TEST !== "true") {
    return NextResponse.json({ detail: "Not Found" }, { status: 404, headers: corsHeaders });
  }

  const body = await request.json().catch(() => null);
  if (typeof body?.input !== "string" || !body.input.startsWith("e2e-create-")) {
    return NextResponse.json({ detail: "Invalid E2E report ID" }, { status: 400, headers: corsHeaders });
  }

  submittedReports.set(body.input, body);
  return NextResponse.json(null, { status: 202, headers: corsHeaders });
}

export async function OPTIONS() {
  return new Response(null, { headers: corsHeaders });
}
