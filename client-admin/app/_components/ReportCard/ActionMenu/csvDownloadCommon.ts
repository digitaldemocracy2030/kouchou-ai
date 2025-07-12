"use server";

import { getApiBaseUrl } from "../../../utils/api";

type CsvDownloadOptions = {
  includeBOM?: boolean;
  filenameSuffix?: string;
  contentType?: string;
};

type CsvDownloadResult =
  | {
      success: true;
      data: string;
      filename: string;
      contentType: string;
    }
  | {
      success: false;
      error: string;
    };

export async function csvDownloadCommon(slug: string, options: CsvDownloadOptions = {}): Promise<CsvDownloadResult> {
  const { includeBOM = false, filenameSuffix = "", contentType = "text/csv" } = options;

  try {
    const response = await fetch(`${getApiBaseUrl()}/admin/comments/${slug}/csv`, {
      headers: {
        "x-api-key": process.env.NEXT_PUBLIC_ADMIN_API_KEY || "",
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      const errorData = await response.json();
      return {
        success: false,
        error: errorData.detail || "CSV ダウンロードに失敗しました",
      };
    }

    const blob = await response.blob();

    if (!includeBOM) {
      const arrayBuffer = await blob.arrayBuffer();
      const csvContent = Buffer.from(arrayBuffer).toString("base64");
      return {
        success: true,
        data: csvContent,
        filename: `kouchou_${slug}${filenameSuffix}.csv`,
        contentType,
      };
    }

    const text = await blob.text();
    const bom = "\uFEFF";
    const csvContent = bom + text;
    const buffer = Buffer.from(csvContent, "utf-8");

    return {
      success: true,
      data: buffer.toString("base64"),
      filename: `kouchou_${slug}${filenameSuffix}.csv`,
      contentType,
    };
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : "予期しないエラーが発生しました",
    };
  }
}
