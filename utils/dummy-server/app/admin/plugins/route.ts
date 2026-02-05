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

  // Minimal plugin list for admin UI during E2E
  return NextResponse.json({ plugins: [] }, { headers: corsHeaders });
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
