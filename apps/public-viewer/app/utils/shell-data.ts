import { getRelativeUrl } from "@/app/utils/image-src";

/**
 * shell ビルドの出力は 1 枚の HTML を各レポートのディレクトリへコピーして配布する。
 * コピー後の HTML には build 時の params（SHELL_SLUG）が埋まったままなので、
 * 表示すべきレポートは URL から求める。
 *
 * @param pathname `location.pathname`（例: "/example/", "/base/example/index.html"）
 * @param basePath `NEXT_PUBLIC_STATIC_EXPORT_BASE_PATH`（例: "/base"、未設定なら ""）
 * @returns レポートの slug。トップなど slug が無い場合は null
 */
export function resolveShellSlug(pathname: string, basePath = ""): string | null {
  let rest = pathname;

  const normalizedBasePath = basePath.replace(/\/+$/, "");
  if (normalizedBasePath && (rest === normalizedBasePath || rest.startsWith(`${normalizedBasePath}/`))) {
    rest = rest.slice(normalizedBasePath.length);
  }

  const segments = rest
    .split("/")
    .filter(Boolean)
    .filter((segment) => segment !== "index.html");

  return segments[0] ?? null;
}

/** 同梱データ（レポート一覧）の URL */
export const getShellReportListUrl = (): string => getRelativeUrl("/data/reports.json");

/** 同梱データ（メタデータ）の URL */
export const getShellMetaUrl = (): string => getRelativeUrl("/data/metadata.json");

/** 同梱データ（レポート本文）の URL */
export const getShellReportUrl = (slug: string): string =>
  getRelativeUrl(`/data/reports/${encodeURIComponent(slug)}.json`);

/**
 * 同梱データを取得する。
 * ビルド時ではなく実行時に読むので、レポートの増減で再ビルドが要らない。
 *
 * @returns 取得した JSON。404 の場合は null
 * @throws 通信そのものに失敗した場合、および 404 以外の異常
 */
export async function fetchShellJson<T>(url: string): Promise<T | null> {
  const response = await fetch(url, { cache: "no-store" });

  if (response.status === 404) {
    return null;
  }

  if (!response.ok) {
    throw new Error(`Failed to load ${url}: ${response.status} ${response.statusText}`);
  }

  return (await response.json()) as T;
}
