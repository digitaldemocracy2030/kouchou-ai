import { ApiConnectionError } from "@/components/ApiConnectionError";
import { Footer } from "@/components/Footer";
import { Header } from "@/components/Header";
import { ReportListContent } from "@/components/report/ReportListContent";
import { Reporter } from "@/components/reporter/Reporter";
import type { Meta, Report } from "@/type";
import { Box, Heading } from "@chakra-ui/react";
import type { Metadata } from "next";
import { connection } from "next/server";
import { getApiBaseUrl } from "./utils/api";
import { ReportListShell } from "@/components/report/ReportListShell";
import { isStaticExportBuild, isStaticShellBuild } from "./utils/static-build";

export const revalidate = 300;

export async function generateMetadata(): Promise<Metadata> {
  if (!isStaticExportBuild()) {
    await connection();
  }

  // shell ビルドはビルド時に API を読まない。
  if (isStaticShellBuild()) {
    return {
      title: "広聴AI",
    };
  }

  try {
    const metaResponse = await fetch(`${getApiBaseUrl()}/meta/metadata.json`);
    const meta: Meta = await metaResponse.json();

    const { getBasePath, getRelativeUrl } = await import("@/app/utils/image-src");

    const metadata: Metadata = {
      title: `${meta.reporter}のレポート一覧 - 広聴AI`,
      description: meta.message || "",
      openGraph: {
        images: [getRelativeUrl("/meta/ogp.png")],
      },
    };

    // 静的エクスポート時はmetadataBaseを設定しない（相対パスを使用するため）
    if (process.env.NEXT_PUBLIC_OUTPUT_MODE !== "export") {
      // 開発環境やSSR時のみmetadataBaseを設定
      const defaultHost = process.env.NEXT_PUBLIC_SITE_URL || "http://localhost:3000";
      metadata.metadataBase = new URL(defaultHost + getBasePath());
    }

    return metadata;
  } catch (_e) {
    console.error("Failed to fetch metadata for generateMetadata:", _e);
    return {
      title: "広聴AI",
    };
  }
}

export default async function Page() {
  if (!isStaticExportBuild()) {
    await connection();
  }

  // shell ビルドではレポート一覧を実行時に同梱 JSON から読む。
  if (isStaticShellBuild()) {
    return <ReportListShell />;
  }

  try {
    const metaResponse = await fetch(`${getApiBaseUrl()}/meta/metadata.json`);
    const reportsResponse = await fetch(`${getApiBaseUrl()}/reports`, {
      headers: {
        "x-api-key": process.env.NEXT_PUBLIC_PUBLIC_API_KEY || "",
        "Content-Type": "application/json",
      },
    });
    const meta: Meta = await metaResponse.json();
    let reports: Report[] = await reportsResponse.json();

    if (process.env.BUILD_SLUGS) {
      reports = reports.filter((report) => process.env.BUILD_SLUGS?.split(",").includes(report.slug));
    }

    return (
      <>
        <Header />
        <Box className="container">
          <Box mx={"auto"} maxW={"1024px"} mb={10} mt="8">
            <Box mb="12">
              <Reporter meta={meta} />
            </Box>
            <Heading textAlign={"left"} fontSize={"xl"} mb={8}>
              レポート一覧
            </Heading>
            <ReportListContent reports={reports} meta={meta} />
          </Box>
        </Box>
        <Footer meta={meta} />
      </>
    );
  } catch (e) {
    const apiUrl = getApiBaseUrl();
    const errorMessage = e instanceof Error ? e.message : String(e);
    return <ApiConnectionError apiUrl={apiUrl} errorMessage={errorMessage} isServerSide={true} />;
  }
}
