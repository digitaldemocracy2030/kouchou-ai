"use server";

import { ADMIN_API_KEY_MISSING_MESSAGE, getApiBaseUrl } from "@/app/utils/api";
import type { Report } from "@/type.d";
import type { PromptSourceReport } from "../utils/promptsFromReport";

type ListResult = { success: true; reports: PromptSourceReport[] } | { success: false; error: string };

/**
 * プロンプトの読み込み元に選べるレポートの一覧を取得する（#1203）。
 * 選択肢に必要な ID・タイトル・作成日時だけを返す。
 */
export async function listPromptSourceReports(): Promise<ListResult> {
  const adminApiKey = process.env.ADMIN_API_KEY;
  if (!adminApiKey) {
    return { success: false, error: ADMIN_API_KEY_MISSING_MESSAGE };
  }
  try {
    const response = await fetch(`${getApiBaseUrl()}/admin/reports`, {
      headers: { "x-api-key": adminApiKey },
      cache: "no-store",
    });
    if (!response.ok) {
      return { success: false, error: `レポート一覧の取得に失敗しました（${response.status}）` };
    }
    const reports: Report[] = await response.json();
    if (!Array.isArray(reports)) {
      return { success: false, error: "レポート一覧の形式が想定と異なります" };
    }
    return {
      success: true,
      reports: reports.map((report) => ({
        slug: report.slug,
        title: report.title,
        createdAt: report.createdAt,
      })),
    };
  } catch (error) {
    console.error("Failed to fetch reports for prompt sources", error);
    return { success: false, error: "レポート一覧の取得に失敗しました" };
  }
}
