import type { SpreadsheetComment } from "../types";
import { handleApiError } from "../utils/error-handler";

/**
 * スプレッドシートをインポートする
 */
export async function importSpreadsheet(url: string, fileName: string): Promise<void> {
  try {
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASEPATH}/admin/spreadsheet/import`, {
      method: "POST",
      headers: {
        "x-api-key": process.env.NEXT_PUBLIC_ADMIN_API_KEY || "",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        url,
        file_name: fileName,
      }),
    });

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || "不明なエラーが発生しました");
    }

    return await response.json();
  } catch (error) {
    throw handleApiError(error, "スプレッドシートのインポートに失敗しました");
  }
}

/**
 * スプレッドシートのデータを取得する
 */
export async function getSpreadsheetData(id: string): Promise<{ comments: SpreadsheetComment[] }> {
  try {
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASEPATH}/admin/spreadsheet/data/${id}`, {
      headers: {
        "x-api-key": process.env.NEXT_PUBLIC_ADMIN_API_KEY || "",
      },
    });

    if (!response.ok) {
      throw new Error("スプレッドシートデータの取得に失敗しました");
    }

    return await response.json();
  } catch (error) {
    throw handleApiError(error, "スプレッドシートデータの取得に失敗しました");
  }
}

/**
 * スプレッドシートのデータを削除する
 */
export async function deleteSpreadsheetData(id: string): Promise<void> {
  try {
    const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASEPATH}/admin/inputs/${id}`, {
      method: "DELETE",
      headers: {
        "x-api-key": process.env.NEXT_PUBLIC_ADMIN_API_KEY || "",
      },
    });

    if (!response.ok) {
      throw new Error("データのクリアに失敗しました");
    }

    return;
  } catch (error) {
    throw handleApiError(error, "データのクリアに失敗しました");
  }
}
