"use server";

import { getApiBaseUrl } from "@/app/utils/api";
import type { CsvData } from "../parseCsv";
import type { PromptSettings } from "../types";

type CreateReportResult = {
  success: boolean;
  error?: string;
};

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
      return { success: false, error: response.statusText };
    }

    return { success: true };
  } catch (error) {
    return { success: false, error: "レポート作成に失敗しました" };
  }
}
