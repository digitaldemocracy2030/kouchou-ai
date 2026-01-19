"use server";

import { getApiBaseUrl } from "../../../utils/api";

type DeleteResult = { success: true } | { success: false; error: string };

export async function reportDelete(slug: string): Promise<DeleteResult> {
  try {
    const response = await fetch(`${getApiBaseUrl()}/admin/reports/${slug}`, {
      method: "DELETE",
      headers: {
        "x-api-key": process.env.NEXT_PUBLIC_ADMIN_API_KEY || "",
        "Content-Type": "application/json",
      },
    });
    if (!response.ok) {
      const errorData = await response.json();
      const errorMessage = errorData.detail || "レポートの削除に失敗しました";
      console.error(new Error(errorMessage));
      return { success: false, error: errorMessage };
    }
    return { success: true };
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : "レポートの削除に失敗しました";
    console.error(error);
    return { success: false, error: errorMessage };
  }
}
