"use server";

import type { ReportVisibility } from "@/type";
import { getApiBaseUrl } from "../../../utils/api";

type Result =
  | {
      success: true;
      visibility: ReportVisibility;
    }
  | {
      success: false;
      error: string;
    };

export async function updateReportVisibility(slug: string, visibility: ReportVisibility): Promise<Result> {
  try {
    const response = await fetch(`${getApiBaseUrl()}/admin/reports/${slug}/visibility`, {
      method: "PATCH",
      headers: {
        "x-api-key": process.env.NEXT_PUBLIC_ADMIN_API_KEY || "",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ visibility }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || "公開状態の変更に失敗しました");
    }

    const data = await response.json();
    return {
      success: true,
      visibility: data.visibility as ReportVisibility,
    };
  } catch (error) {
    console.error(error);
    return {
      success: false,
      error: error instanceof Error ? error.message : "公開状態の変更に失敗しました",
    };
  }
}
