"use server";

import { getApiBaseUrl } from "@/app/utils/api";

type DuplicateParams = {
  newSlug?: string;
  overviewPrompt?: string;
  reuseEnabled: boolean;
};

type DuplicateResult = { success: true; slug: string } | { success: false; error: string };

export async function duplicateReport(sourceSlug: string, params: DuplicateParams): Promise<DuplicateResult> {
  const adminApiKey = process.env.ADMIN_API_KEY;
  if (!adminApiKey) {
    throw new Error("ADMIN_API_KEY is not set");
  }

  const body: Record<string, unknown> = {
    reuse: { enabled: params.reuseEnabled },
  };

  if (params.newSlug) {
    body.newSlug = params.newSlug;
  }

  if (params.overviewPrompt) {
    body.overrides = {
      prompt: {
        overview: params.overviewPrompt,
      },
    };
  }

  try {
    const response = await fetch(`${getApiBaseUrl()}/admin/reports/${sourceSlug}/duplicate`, {
      method: "POST",
      headers: {
        "x-api-key": adminApiKey,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      const errorData = await response.json();
      return { success: false, error: errorData.detail || "レポートの複製に失敗しました" };
    }

    const data = await response.json();
    const slug = data?.report?.slug || params.newSlug;
    if (!slug) {
      console.warn("Duplicate succeeded but no slug returned from API", data);
      return { success: false, error: "複製は成功しましたが、新しいレポートのIDを取得できませんでした" };
    }
    return { success: true, slug };
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : "レポートの複製に失敗しました";
    return { success: false, error: errorMessage };
  }
}
