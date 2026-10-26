"use server";

import { ADMIN_API_KEY_MISSING_MESSAGE, getApiBaseUrl } from "@/app/utils/api";

type DuplicateParams = {
  newSlug?: string;
  reuseEnabled: boolean;
  // 再実行するステップで使うユーザー入力の API キー。本文ではなく x-user-api-key ヘッダーで送る
  userApiKey?: string;
  overrides?: {
    question?: string;
    intro?: string;
    provider?: string;
    model?: string;
    cluster?: number[];
    prompt?: {
      extraction?: string;
      initial_labelling?: string;
      merge_labelling?: string;
      overview?: string;
    };
  };
};

type DuplicateResult = { success: true; slug: string } | { success: false; error: string };

export async function duplicateReport(sourceSlug: string, params: DuplicateParams): Promise<DuplicateResult> {
  const adminApiKey = process.env.ADMIN_API_KEY;
  if (!adminApiKey) {
    throw new Error(ADMIN_API_KEY_MISSING_MESSAGE);
  }
  const encodedSourceSlug = encodeURIComponent(sourceSlug);

  const body: Record<string, unknown> = {
    reuse: { enabled: params.reuseEnabled },
  };

  if (params.newSlug) {
    body.newSlug = params.newSlug;
  }

  if (params.overrides) {
    body.overrides = params.overrides;
  }

  const headers: Record<string, string> = {
    "x-api-key": adminApiKey,
    "Content-Type": "application/json",
  };
  if (params.userApiKey) {
    headers["x-user-api-key"] = params.userApiKey;
  }

  try {
    const response = await fetch(`${getApiBaseUrl()}/admin/reports/${encodedSourceSlug}/duplicate`, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
      // x-user-api-key は fetch のリダイレクトで外されないので、リダイレクト先へ鍵を転送しない
      redirect: "error",
    });

    if (!response.ok) {
      const errorData = await response.json();
      return { success: false, error: errorData.detail || "レポートの再利用に失敗しました" };
    }

    const data = await response.json();
    const slug = data?.report?.slug || params.newSlug;
    if (!slug) {
      console.warn("Duplicate succeeded but no slug returned from API", data);
      return { success: false, error: "再利用は成功しましたが、新しいレポートのIDを取得できませんでした" };
    }
    return { success: true, slug };
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : "レポートの再利用に失敗しました";
    return { success: false, error: errorMessage };
  }
}
