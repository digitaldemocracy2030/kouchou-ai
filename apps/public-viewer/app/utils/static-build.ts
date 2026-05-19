import type { Report } from "@/type";

type StaticBuildSlug = {
  slug: string;
};

const formatBuildSlugList = (slugs: string[]) => slugs.map((slug) => `"${slug}"`).join(", ");

export const isStaticExportBuild = () => process.env.NEXT_PUBLIC_OUTPUT_MODE === "export";

export const parseBuildSlugs = (buildSlugs = process.env.BUILD_SLUGS): string[] =>
  buildSlugs
    ?.split(",")
    .map((slug) => slug.trim())
    .filter(Boolean) || [];

export function getStaticBuildReportSlugs(reports: Report[], buildSlugs = process.env.BUILD_SLUGS): StaticBuildSlug[] {
  const readyReports = reports.filter((report) => report.status === "ready");
  const readySlugs = readyReports.map((report) => report.slug);
  const requestedSlugs = parseBuildSlugs(buildSlugs);

  if (isStaticExportBuild() && readySlugs.length === 0) {
    throw new Error(
      [
        "静的HTML出力に必要な公開状態のレポートが見つかりませんでした。",
        "少なくとも1件のレポートを公開状態（status: ready）にしてから再実行してください。",
      ].join(" "),
    );
  }

  if (requestedSlugs.length === 0) {
    return readySlugs.map((slug) => ({ slug }));
  }

  const selectedReadySlugs = readySlugs.filter((slug) => requestedSlugs.includes(slug));

  if (isStaticExportBuild() && selectedReadySlugs.length === 0) {
    throw new Error(
      [
        "BUILD_SLUGS で指定されたレポートが、公開状態（status: ready）の一覧に見つかりませんでした。",
        `指定値: ${formatBuildSlugList(requestedSlugs)}`,
        `公開状態の slug: ${readySlugs.length > 0 ? formatBuildSlugList(readySlugs) : "なし"}`,
      ].join(" "),
    );
  }

  return selectedReadySlugs.map((slug) => ({ slug }));
}

export function createStaticBuildFetchError(error: unknown): Error {
  const message = error instanceof Error ? error.message : String(error);

  return new Error(
    [
      "静的HTML出力の事前確認でレポート一覧の取得に失敗しました。",
      "APIサーバーが起動しているか、API_BASEPATH / NEXT_PUBLIC_API_BASEPATH の設定が正しいか確認してください。",
      `元エラー: ${message}`,
    ].join(" "),
  );
}
