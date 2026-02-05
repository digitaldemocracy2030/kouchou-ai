import { NextResponse } from "next/server";

const usedSlugs = new Set<string>();

export async function POST(request: Request, context: { params: Promise<{ slug: string }> }) {
  const requestApiKey = request.headers.get("x-api-key");
  const validApiKey = process.env.ADMIN_API_KEY;
  const corsHeaders = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type, x-api-key",
  };

  if (!requestApiKey || requestApiKey !== validApiKey) {
    return NextResponse.json({ error: "Unauthorized", detail: "Unauthorized" }, { status: 401, headers: corsHeaders });
  }

  const body = await request.json().catch(() => ({}));
  const { slug } = await context.params;
  const newSlug = body?.newSlug || `${slug}-copy-20250101`;

  if (usedSlugs.has(newSlug)) {
    return NextResponse.json(
      { error: "newSlug already exists", detail: "newSlug already exists" },
      { status: 409, headers: corsHeaders }
    );
  }
  usedSlugs.add(newSlug);

  return NextResponse.json(
    {
      success: true,
      report: { slug: newSlug, status: "processing" },
    },
    { headers: corsHeaders }
  );
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
