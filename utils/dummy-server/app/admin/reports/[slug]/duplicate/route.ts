import { NextResponse } from "next/server";

export async function POST(request: Request, context: { params: Promise<{ slug: string }> }) {
  const requestApiKey = request.headers.get("x-api-key");
  const validApiKey = process.env.PUBLIC_API_KEY;

  if (!requestApiKey || requestApiKey !== validApiKey) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const body = await request.json().catch(() => ({}));
  const { slug } = await context.params;
  const newSlug = body?.newSlug || `${slug}-copy-20250101`;

  return NextResponse.json({
    success: true,
    report: { slug: newSlug, status: "processing" },
  });
}

export async function OPTIONS() {
  return new Response(null, {
    headers: {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type, x-api-key",
    },
  });
}
