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
  workers,
  prompt,
  is_pubcom,
  inputType,
  is_embedded_at_local,
  enable_source_link,
  local_llm_address,
}: {
  input: string;
  question: string;
  intro: string;
  comments: CsvData[];
  cluster: [number, number];
  provider: string;
  model: string;
  workers: number;
  prompt: PromptSettings;
  is_pubcom: boolean;
  inputType: string;
  is_embedded_at_local: boolean;
  enable_source_link: boolean;
  local_llm_address?: string;
}): Promise<CreateReportResult> {
  try {
    const response = await fetch(`${getApiBaseUrl()}/admin/reports`, {
      method: "POST",
      headers: {
        "x-api-key": process.env.NEXT_PUBLIC_ADMIN_API_KEY || "",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        input,
        question,
        intro,
        comments,
        cluster,
        provider,
        model,
        workers,
        prompt,
        is_pubcom,
        inputType,
        is_embedded_at_local,
        enable_source_link,
        local_llm_address,
      }),
    });

    if (!response.ok) {
      return { success: false, error: response.statusText };
    }

    return { success: true };
  } catch (error) {
    return { success: false, error: "レポート作成に失敗しました" };
  }
}
