"use server";

import { getApiBaseUrl } from "@/app/utils/api";
import type { ReportDisplayConfig } from "@/type";

type FetchVisualizationConfigResult =
  | {
      success: true;
      config: ReportDisplayConfig | null;
    }
  | {
      success: false;
      error: string;
    };

export async function fetchVisualizationConfig(reportSlug: string): Promise<FetchVisualizationConfigResult> {
  try {
    const response = await fetch(`${getApiBaseUrl()}/admin/reports/${reportSlug}/visualization-config`, {
      headers: {
        "x-api-key": process.env.NEXT_PUBLIC_ADMIN_API_KEY || "",
      },
    });

    if (!response.ok) {
      return { success: false, error: "可視化設定の取得に失敗しました" };
    }

    const data = await response.json();
    return { success: true, config: data.visualizationConfig };
  } catch (error) {
    return { success: false, error: "可視化設定の取得に失敗しました" };
  }
}

type UpdateVisualizationConfigResult = {
  success: boolean;
  config?: ReportDisplayConfig;
  error?: string;
};

export async function updateVisualizationConfig(
  reportSlug: string,
  config: ReportDisplayConfig,
): Promise<UpdateVisualizationConfigResult> {
  try {
    const response = await fetch(`${getApiBaseUrl()}/admin/reports/${reportSlug}/visualization-config`, {
      method: "PATCH",
      headers: {
        "x-api-key": process.env.NEXT_PUBLIC_ADMIN_API_KEY || "",
        "Content-Type": "application/json",
      },
      body: JSON.stringify(config),
    });

    if (!response.ok) {
      const errorData = await response.json();
      let errorMessage = errorData.detail || "可視化設定の更新に失敗しました";
      if (response.status === 400) {
        errorMessage = `入力データが不正です: ${errorMessage}`;
      } else if (response.status === 404) {
        errorMessage = "指定されたレポートが見つかりません";
      }
      return { success: false, error: errorMessage };
    }

    const data = await response.json();
    return { success: true, config: data.visualizationConfig };
  } catch (error) {
    return { success: false, error: "可視化設定の更新に失敗しました" };
  }
}
