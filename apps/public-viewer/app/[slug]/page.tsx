import { ReportShell } from "@/components/report/ReportShell";
import { ReportView } from "@/components/report/ReportView";
import { Reporter } from "@/components/reporter/Reporter";
import type { Meta, Report, Result } from "@/type";
import { ReportVisibility } from "@/type";
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { getApiBaseUrl } from "../utils/api";
import {
  SHELL_SLUG,
  createStaticBuildFetchError,
  getStaticBuildReportSlugs,
  isStaticExportBuild,
  isStaticShellBuild,
} from "../utils/static-build";

type PageProps = {
  params: Promise<{
    slug: string;
  }>;
};

// ISR 5分おきにレポート更新確認
export const revalidate = 300;

export async function generateStaticParams() {
  if (!isStaticExportBuild()) {
    return [];
  }

  // shell ビルドはレポートに依存しない 1 ルートだけを出力する。
  // 実際のレポートは配布時にこのディレクトリを slug へコピーして表示する。
  if (isStaticShellBuild()) {
    return [{ slug: SHELL_SLUG }];
  }

  let reports: Report[];

  try {
    const response = await fetch(`${getApiBaseUrl()}/reports`, {
      headers: {
        "x-api-key": process.env.NEXT_PUBLIC_PUBLIC_API_KEY || "",
        "Content-Type": "application/json",
      },
    });
    if (!response.ok) {
      throw new Error(`Failed to fetch reports: ${response.status} ${response.statusText}`);
    }
    reports = await response.json();
  } catch (error) {
    if (isStaticExportBuild()) {
      throw createStaticBuildFetchError(error);
    }

    return [];
  }

  return getStaticBuildReportSlugs(reports);
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  // shell ビルドはビルド時にレポートを読まないので、タイトルもレポートに依存させない。
  if (isStaticShellBuild()) {
    // The Python packager and shell navigation own per-report head metadata.
    return {};
  }

  const { getMetadataBase } = await import("@/app/utils/image-src");

  // SSR / ISR でもレポートを取得して metadata を作る。限定公開レポートに noindex を
  // 付けるためで、fetch は Page 本体と同じ URL・tag なので重複排除される。
  // 取得に失敗したときの既定値にも metadataBase を付ける。無いと SSR では og:image
  // （opengraph-image）が Next の既定の http://localhost:<PORT> を指してしまう。
  // NEXT_PUBLIC_SITE_URL が不正だと getMetadataBase() が例外を投げるので、try の中で付ける。
  const fallbackMetadata: Metadata = isStaticExportBuild() ? {} : { title: "広聴AI" };

  try {
    if (!isStaticExportBuild()) {
      const metadataBase = getMetadataBase();
      if (metadataBase) fallbackMetadata.metadataBase = metadataBase;
    }
    const slug = (await params).slug;
    const metaResponse = await fetch(`${getApiBaseUrl()}/meta/metadata.json`, {
      next: { tags: ["meta"] },
    });
    const resultResponse = await fetch(`${getApiBaseUrl()}/reports/${slug}`, {
      headers: {
        "x-api-key": process.env.NEXT_PUBLIC_PUBLIC_API_KEY || "",
        "Content-Type": "application/json",
      },
      next: { tags: [`report-${slug}`] },
    });
    if (!resultResponse.ok) {
      return fallbackMetadata;
    }

    const result: Result = await resultResponse.json();
    // visibilityが"unlisted"の場合、noindexを設定（meta の取得に失敗しても付ける）
    const robots: Metadata["robots"] =
      result.visibility === ReportVisibility.UNLISTED ? { index: false, follow: false } : undefined;

    if (!metaResponse.ok) {
      return robots ? { ...fallbackMetadata, robots } : fallbackMetadata;
    }

    const meta: Meta = await metaResponse.json();
    const metaData: Metadata = {
      title: meta.reporter ? `${result.config.question} - ${meta.reporter}` : result.config.question,
      description: `${result.overview}`,
    };

    if (robots) {
      metaData.robots = robots;
    }

    // og:image などの相対 URL を公開先の絶対 URL に解決させる（静的エクスポート時も必要）
    const metadataBase = getMetadataBase();
    if (metadataBase) {
      metaData.metadataBase = metadataBase;
    }

    if (process.env.NEXT_PUBLIC_OUTPUT_MODE === "export") {
      // 静的書き出しではレポート別の OGP 画像（opengraph-image）を生成しない
      // （scripts/rename-file.mjs がビルド対象から外す）ので、copy-image が出力に置く共通画像を指す。
      // metadataBase がベースパスを含むので、ここではベースパスを付けない
      metaData.openGraph = {
        images: ["/meta/ogp.png"],
      };
    }

    return metaData;
  } catch (_e) {
    return fallbackMetadata;
  }
}

export default async function Page({ params }: PageProps) {
  // shell ビルドではレポートを実行時に同梱 JSON から読む。
  if (isStaticShellBuild()) {
    return <ReportShell />;
  }

  const slug = (await params).slug;
  const apiUrl = getApiBaseUrl();

  // fetch の失敗は握りつぶさずに throw する。エラー画面を正常な描画として返すと
  // ISR がそれをキャッシュし、正常なページを置き換えてしまう。throw すれば再生成の
  // 失敗時は古いページが残り、初回描画では error.tsx が使われる。
  const metaResponse = await fetch(`${apiUrl}/meta/metadata.json`, {
    next: { tags: ["meta"] },
  });
  const resultResponse = await fetch(`${apiUrl}/reports/${slug}`, {
    headers: {
      "x-api-key": process.env.NEXT_PUBLIC_PUBLIC_API_KEY || "",
      "Content-Type": "application/json",
    },
    next: { tags: [`report-${slug}`] },
  });

  if (metaResponse.status === 404 || resultResponse.status === 404) {
    notFound();
  }
  // 404 以外の失敗（API の 5xx など）も、エラーの応答をレポートとして描画せずに throw する
  if (!metaResponse.ok || !resultResponse.ok) {
    throw new Error(`Failed to fetch report: meta=${metaResponse.status}, result=${resultResponse.status}`);
  }

  const meta: Meta = await metaResponse.json();
  const result: Result = await resultResponse.json();

  return <ReportView result={result} meta={meta} reporter={<Reporter meta={meta} />} />;
}
