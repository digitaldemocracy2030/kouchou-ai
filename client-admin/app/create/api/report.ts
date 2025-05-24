import type { CsvData } from "../parseCsv";
import type { PromptSettings } from "../types";
import { handleApiError } from "../utils/error-handler";

/**
 * レポート作成APIを呼び出す
 */
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
  local_llm_address,
  skip_extraction,
  skip_initial_labelling,
  skip_merge_labelling,
  skip_overview,
  auto_cluster_enabled,
  cluster_top_min,
  cluster_top_max,
  cluster_bottom_max,
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
  local_llm_address?: string;
  skip_extraction?: boolean;
  skip_initial_labelling?: boolean;
  skip_merge_labelling?: boolean;
  skip_overview?: boolean;
  auto_cluster_enabled?: boolean;
  cluster_top_min?: number;
  cluster_top_max?: number;
  cluster_bottom_max?: number;
}): Promise<void> {
  try {
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASEPATH}/admin/reports`, {
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
        local_llm_address,
        skip_extraction,
        skip_initial_labelling,
        skip_merge_labelling,
        skip_overview,
        auto_cluster_enabled,
        cluster_top_min,
        cluster_top_max,
        cluster_bottom_max,
      }),
    });

    if (!response.ok) {
      throw new Error(response.statusText);
    }

    return;
  } catch (error) {
    throw handleApiError(error, "レポート作成に失敗しました");
  }
}
