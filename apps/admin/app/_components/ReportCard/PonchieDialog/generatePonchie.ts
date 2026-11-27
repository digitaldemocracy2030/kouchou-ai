"use server";

import { getApiBaseUrl } from "@/app/utils/api";

export async function generatePonchie(slug: string) {
  const baseUrl = getApiBaseUrl();
  const key = process.env.ADMIN_API_KEY || process.env.NEXT_PUBLIC_ADMIN_API_KEY;
  if (!baseUrl || !key) return { ok: false, error: "管理 API が設定されていません。" } as const;
  try {
    const response = await fetch(`${baseUrl}/admin/reports/${encodeURIComponent(slug)}/ponchie`, {
      method: "POST",
      cache: "no-store",
      headers: { "x-api-key": key },
    });
    if (!response.ok) {
      const { detail } = await response.json().catch(() => ({}));
      return { ok: false, error: typeof detail === "string" ? detail : "ポンチ絵を生成できませんでした。" } as const;
    }
    return { ok: true, data: Buffer.from(await response.arrayBuffer()).toString("base64") } as const;
  } catch {
    return { ok: false, error: "画像生成に接続できませんでした。" } as const;
  }
}
