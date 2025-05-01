import { CsvData } from "../parseCsv";
import { PromptSettings } from "../types";
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
  model,
  provider,
  workers,
  prompt,
  is_pubcom,
  inputType,
  is_embedded_at_local,
}: {
  input: string;
  question: string;
  intro: string;
  comments: CsvData[];
  cluster: [number, number];
  model: string;
  provider: string;
  workers: number;
  prompt: PromptSettings;
  is_pubcom: boolean;
  inputType: string;
  is_embedded_at_local: boolean;
}): Promise<void> {
  try {
    const response = await fetch(
      `${process.env.NEXT_PUBLIC_API_BASEPATH}/admin/reports`,
      {
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
          model,
          provider,
          workers,
          prompt,
          is_pubcom,
          inputType,
          is_embedded_at_local,
        }),
      }
    );

    if (!response.ok) {
      throw new Error(response.statusText);
    }

    return;
  } catch (error) {
    throw handleApiError(error, "レポート作成に失敗しました");
  }
}
