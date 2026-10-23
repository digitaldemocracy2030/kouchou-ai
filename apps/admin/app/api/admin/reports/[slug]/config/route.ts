import { ADMIN_API_KEY_MISSING_MESSAGE } from "@/app/utils/api";
import { NextResponse } from "next/server";

const getAdminBaseUrl = () => {
  return process.env.API_BASEPATH || process.env.NEXT_PUBLIC_API_BASEPATH || "";
};

export async function GET(_: Request, context: { params: Promise<{ slug: string }> }) {
  const adminApiKey = process.env.ADMIN_API_KEY;
  if (!adminApiKey) {
    return NextResponse.json({ detail: ADMIN_API_KEY_MISSING_MESSAGE }, { status: 500 });
  }

  const baseUrl = getAdminBaseUrl();
  if (!baseUrl) {
    return NextResponse.json({ detail: "API base URL is not configured" }, { status: 500 });
  }

  const { slug } = await context.params;
  const encodedSlug = encodeURIComponent(slug);
  try {
    const response = await fetch(`${baseUrl}/admin/reports/${encodedSlug}/config`, {
      headers: {
        "x-api-key": adminApiKey,
      },
    });

    const data = await response.json().catch(() => ({}));
    return NextResponse.json(data, { status: response.status });
  } catch (error) {
    console.error("Failed to fetch report config", error);
    return NextResponse.json({ detail: "Failed to fetch report config" }, { status: 500 });
  }
}
