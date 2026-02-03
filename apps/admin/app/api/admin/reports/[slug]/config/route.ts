import { NextResponse } from "next/server";

const getAdminBaseUrl = () => {
  return process.env.API_BASEPATH || process.env.NEXT_PUBLIC_API_BASEPATH || "";
};

export async function GET(_: Request, context: { params: Promise<{ slug: string }> }) {
  const adminApiKey = process.env.ADMIN_API_KEY;
  if (!adminApiKey) {
    return NextResponse.json({ error: "ADMIN_API_KEY is not set" }, { status: 500 });
  }

  const baseUrl = getAdminBaseUrl();
  if (!baseUrl) {
    return NextResponse.json({ error: "API base URL is not configured" }, { status: 500 });
  }

  const { slug } = await context.params;
  try {
    const response = await fetch(`${baseUrl}/admin/reports/${slug}/config`, {
      headers: {
        "x-api-key": adminApiKey,
      },
    });

    const data = await response.json().catch(() => ({}));
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    const message = error instanceof Error ? error.message : "Failed to fetch report config";
    return NextResponse.json({ error: message }, { status: 500 });
  }
}
