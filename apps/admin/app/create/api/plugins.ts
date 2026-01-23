"use server";

import { getApiBaseUrl } from "@/app/utils/api";
import type { PluginImportResult, PluginManifest, PluginPreviewResult } from "@/type.d";

/**
 * 利用可能なプラグイン一覧を取得
 */
export async function getPlugins(): Promise<PluginManifest[]> {
  const response = await fetch(`${getApiBaseUrl()}/admin/plugins`, {
    headers: {
      "x-api-key": process.env.NEXT_PUBLIC_ADMIN_API_KEY || "",
    },
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`Failed to fetch plugins: ${response.statusText}`);
  }

  const data = await response.json();
  return data.plugins;
}

/**
 * プラグインのソースURLを検証
 */
export async function validatePluginSource(
  pluginId: string,
  source: string,
): Promise<{ isValid: boolean; error: string | null }> {
  const response = await fetch(`${getApiBaseUrl()}/admin/plugins/${pluginId}/validate-source`, {
    method: "POST",
    headers: {
      "x-api-key": process.env.NEXT_PUBLIC_ADMIN_API_KEY || "",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ pluginId, source }),
  });

  if (!response.ok) {
    throw new Error(`Failed to validate source: ${response.statusText}`);
  }

  return response.json();
}

/**
 * プラグインからデータをプレビュー
 */
export async function previewPluginData(pluginId: string, source: string, limit = 10): Promise<PluginPreviewResult> {
  const response = await fetch(`${getApiBaseUrl()}/admin/plugins/${pluginId}/preview`, {
    method: "POST",
    headers: {
      "x-api-key": process.env.NEXT_PUBLIC_ADMIN_API_KEY || "",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ source, limit }),
  });

  if (!response.ok) {
    throw new Error(`Failed to preview data: ${response.statusText}`);
  }

  return response.json();
}

/**
 * プラグインからデータをインポート
 */
export async function importPluginData(
  pluginId: string,
  source: string,
  fileName: string,
  maxResults = 1000,
  includeReplies = false,
): Promise<PluginImportResult> {
  const response = await fetch(`${getApiBaseUrl()}/admin/plugins/${pluginId}/import`, {
    method: "POST",
    headers: {
      "x-api-key": process.env.NEXT_PUBLIC_ADMIN_API_KEY || "",
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      source,
      fileName,
      maxResults,
      includeReplies,
    }),
  });

  if (!response.ok) {
    throw new Error(`Failed to import data: ${response.statusText}`);
  }

  return response.json();
}
