"use server";

import { getApiBaseUrl } from "@/app/utils/api";
import type { CsvData } from "../parseCsv";
import type { PromptSettings } from "../types";

type CreateReportResult = {
  success: boolean;
  error?: string;
};

type ValidationErrorItem = {
  loc?: unknown;
  msg?: unknown;
};

// API のエラーレスポンスから表示用メッセージを取り出す。
// detail は文字列（HTTPException）か、422 のときは { loc, msg } の配列になる。
async function extractErrorMessage(response: Response): Promise<string> {
  const errorData = await response.json().catch(() => ({}));
  const detail = errorData?.detail;
  if (typeof detail === "string" && detail) {
    return detail;
  }
  if (Array.isArray(detail) && detail.length > 0) {
    return detail
      .map((item: ValidationErrorItem) => {
        const loc = Array.isArray(item?.loc) ? item.loc.join(".") : "";
        const msg = typeof item?.msg === "string" ? item.msg : "";
        return loc ? `${loc}: ${msg}` : msg;
      })
      .join(" / ");
  }
  return response.statusText || "レポート作成に失敗しました";
}

export async function createReport({
  input,
  question,
  intro,
  comments,
  cluster,
  provider,
  model,
  embedding_model,
  workers,
  prompt,
  analysis_mode,
  is_pubcom,
  inputType,
  is_embedded_at_local,
  enable_source_link,
  local_llm_address,
  userApiKey,
}: {
  input: string;
  question: string;
  intro: string;
  comments: CsvData[];
  cluster: [number, number];
  provider: string;
  model: string;
  embedding_model?: string;
  workers: number;
  prompt: PromptSettings;
  analysis_mode: string;
  is_pubcom: boolean;
  inputType: string;
  is_embedded_at_local: boolean;
  enable_source_link: boolean;
  local_llm_address?: string;
  userApiKey?: string;
}): Promise<CreateReportResult> {
  try {
    const headers: Record<string, string> = {
      "x-api-key": process.env.NEXT_PUBLIC_ADMIN_API_KEY || "",
      "Content-Type": "application/json",
    };

    if (userApiKey) {
      headers["x-user-api-key"] = userApiKey;
    }

    const response = await fetch(`${getApiBaseUrl()}/admin/reports`, {
      method: "POST",
      headers,
      body: JSON.stringify({
        input,
        question,
        intro,
        comments,
        cluster,
        provider,
        model,
        embedding_model,
        workers,
        prompt,
        analysis_mode,
        is_pubcom,
        inputType,
        is_embedded_at_local,
        enable_source_link,
        local_llm_address,
      }),
    });

    if (response.status === 409) {
      // 既存（削除済みを含む）のレポートと同じ ID は API 側で拒否される
      return { success: false, error: "同じIDのレポートが既に存在します。別のIDを指定してください" };
    }

    if (!response.ok) {
      return { success: false, error: await extractErrorMessage(response) };
    }

    return { success: true };
  } catch (error) {
    return { success: false, error: "レポート作成に失敗しました" };
  }
}
