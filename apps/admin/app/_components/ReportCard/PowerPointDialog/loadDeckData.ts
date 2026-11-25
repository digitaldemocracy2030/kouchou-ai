"use server";

import { getApiBaseUrl } from "@/app/utils/api";
import { getDeckData } from "./deckData";

export async function loadDeckData(slug: string) {
  const baseUrl = getApiBaseUrl();
  const key = process.env.ADMIN_API_KEY || process.env.NEXT_PUBLIC_ADMIN_API_KEY;
  if (!baseUrl || !key) return { ok: false, error: "管理 API が設定されていません。" } as const;
  try {
    const response = await fetch(`${baseUrl}/admin/reports/${encodeURIComponent(slug)}/json`, {
      cache: "no-store",
      headers: { "x-api-key": key },
    });
    if (!response.ok) return { ok: false, error: "分析結果を取得できませんでした。" } as const;
    return { ok: true, data: getDeckData(await response.json()) } as const;
  } catch {
    return { ok: false, error: "分析結果を読み込めませんでした。" } as const;
  }
}
