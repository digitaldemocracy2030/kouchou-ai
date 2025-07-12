import { getApiBaseUrl } from "../../../utils/api";

export async function reportDelete(slug: string) {
  try {
    const response = await fetch(`${getApiBaseUrl()}/admin/reports/${slug}`, {
      method: "DELETE",
      headers: {
        "x-api-key": process.env.NEXT_PUBLIC_ADMIN_API_KEY || "",
        "Content-Type": "application/json",
      },
    });
    if (response.ok) {
      window.location.reload();
    } else {
      const errorData = await response.json();
      throw new Error(errorData.detail || "レポートの削除に失敗しました");
    }
  } catch (error) {
    console.error(error);
  }
}
