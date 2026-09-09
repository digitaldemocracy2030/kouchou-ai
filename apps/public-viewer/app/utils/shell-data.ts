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
 * 同梱データの取得に失敗したことを表す。
 * どのファイルで失敗したかを画面に出すため url を持つ。
 */
export class ShellDataFetchError extends Error {
  readonly url: string;

  constructor(url: string, message: string) {
    super(message);
    this.name = "ShellDataFetchError";
    this.url = url;
  }
}

/**
 * 同梱データを取得する。
 * ビルド時ではなく実行時に読むので、レポートの増減で再ビルドが要らない。
 *
 * @returns 取得した JSON。404 の場合は null
 * @throws {ShellDataFetchError} 通信の失敗・404 以外の異常・JSON の破損
 */
export async function fetchShellJson<T>(url: string): Promise<T | null> {
  let response: Response;

  try {
    response = await fetch(url, { cache: "no-store" });
  } catch (e) {
    throw new ShellDataFetchError(url, e instanceof Error ? e.message : String(e));
  }

  if (response.status === 404) {
    return null;
  }

  if (!response.ok) {
    throw new ShellDataFetchError(url, `${response.status} ${response.statusText}`);
  }

  try {
    return (await response.json()) as T;
  } catch (e) {
    throw new ShellDataFetchError(url, `JSON として読めませんでした: ${e instanceof Error ? e.message : String(e)}`);
  }
}
