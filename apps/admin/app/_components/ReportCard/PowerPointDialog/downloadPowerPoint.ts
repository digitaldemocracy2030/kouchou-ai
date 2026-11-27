"use server";

import { getApiBaseUrl } from "@/app/utils/api";
import { headers } from "next/headers";
import { type CoverImage, createPowerPoint, makeReportUrl } from "./createPowerPoint";
import { getDeckData } from "./deckData";

const MAX_COVER_BYTES = 8 * 1024 * 1024;
const COVER_FORMAT = /^data:image\/(?:png;base64,iVBORw0KGgo|jpeg;base64,\/9j\/)/;

function isValidCover(cover: CoverImage): boolean {
  return (
    typeof cover.data === "string" &&
    cover.data.length <= Math.ceil(MAX_COVER_BYTES / 3) * 4 + 32 &&
    COVER_FORMAT.test(cover.data) &&
    Number.isSafeInteger(cover.width) &&
    cover.width > 0 &&
    Number.isSafeInteger(cover.height) &&
    cover.height > 0
  );
}

export async function downloadPowerPoint(slug: string, includeReportLink: boolean, cover?: CoverImage) {
  const baseUrl = getApiBaseUrl();
  const key = process.env.ADMIN_API_KEY || process.env.NEXT_PUBLIC_ADMIN_API_KEY;
  if (!baseUrl || !key) return { ok: false, error: "管理 API が設定されていません。" } as const;
  if (cover && !isValidCover(cover)) return { ok: false, error: "表紙画像を読み込めませんでした。" } as const;
  try {
    const response = await fetch(`${baseUrl}/admin/reports/${encodeURIComponent(slug)}/json`, {
      cache: "no-store",
      headers: { "x-api-key": key },
    });
    if (!response.ok) return { ok: false, error: "分析結果を取得できませんでした。" } as const;
    const result = getDeckData(await response.json());
    const viewer = process.env.NEXT_PUBLIC_CLIENT_BASEPATH;
    const origin = (await headers()).get("origin") ?? "";
    const reportUrl = includeReportLink && viewer ? makeReportUrl(viewer, origin, slug) : undefined;
    const pptx = await createPowerPoint(result, reportUrl, cover).write({ outputType: "nodebuffer" });
    if (!Buffer.isBuffer(pptx)) return { ok: false, error: "PowerPoint を書き出せませんでした。" } as const;
    return {
      ok: true,
      data: pptx.toString("base64"),
      filename: `kouchou_${slug}.pptx`,
      contentType: "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    } as const;
  } catch {
    return { ok: false, error: "PowerPoint を書き出せませんでした。" } as const;
  }
}
