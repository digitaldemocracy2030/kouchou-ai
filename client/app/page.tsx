import { About } from "@/components/About";
import { Footer } from "@/components/Footer";
import { Header } from "@/components/Header";
import type { Meta, Report } from "@/type";
import { Box, Card, HStack, Heading, Text, VStack } from "@chakra-ui/react";
import type { Metadata } from "next";
import Link from "next/link";
import { getApiBaseUrl } from "./utils/api";

export const revalidate = 300;

export async function generateMetadata(): Promise<Metadata> {
  try {
    const metaResponse = await fetch(`${getApiBaseUrl()}/meta/metadata.json`);
    const meta: Meta = await metaResponse.json();

    const { getBasePath, getRelativeUrl } = await import("@/app/utils/image-src");

    const metadata: Metadata = {
      title: `${meta.reporter} - 広聴AI(デジタル民主主義2030ブロードリスニング)`,
      description: meta.message || "",
      openGraph: {
        images: [getRelativeUrl('/meta/ogp.png')],
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
      title: "広聴AI(デジタル民主主義2030ブロードリスニング)",
    };
  }
}

export default async function Page() {
  try {
    const metaResponse = await fetch(`${getApiBaseUrl()}/meta/metadata.json`);
    const reportsResponse = await fetch(`${getApiBaseUrl()}/reports`, {
      headers: {
        "x-api-key": process.env.NEXT_PUBLIC_PUBLIC_API_KEY || "",
        "Content-Type": "application/json",
      },
    });
    const meta: Meta = await metaResponse.json();
    const reports: Report[] = await reportsResponse.json();
    return (
      <>
        <div className={"container"}>
          {meta && <Header meta={meta} />}
          <Box mx={"auto"} maxW={"900px"} mb={10}>
            <Heading textAlign={"center"} fontSize={"xl"} mb={5}>
              Reports
            </Heading>
            {!reports && (
              <VStack my={10}>
                <Text>レポートがありません</Text>
              </VStack>
            )}
            {reports.length > 0 &&
              reports.map((report) => (
                <Link key={report.slug} href={`/${report.slug}`}>
                  <Card.Root
                    size="md"
                    key={report.slug}
                    mb={4}
                    borderLeftWidth={10}
                    borderLeftColor={meta.brandColor || "#2577b1"}
                    cursor={"pointer"}
                    className={"shadow"}
                  >
                    <Card.Body>
                      <HStack>
                        <Box>
                          <Card.Title>
                            <Text fontSize={"lg"} color={"#2577b1"} mb={1}>
                              {report.title}
                            </Text>
                          </Card.Title>
                          {report.createdAt && (
                            <Text fontSize={"xs"} color={"gray.500"} mb={1}>
                              作成日時:{" "}
                              {new Date(report.createdAt).toLocaleString(
                                "ja-JP",
                                { timeZone: "Asia/Tokyo" },
                              )}
                            </Text>
                          )}
                          <Card.Description>
                            {report.description || ""}
                          </Card.Description>
                        </Box>
                      </HStack>
                    </Card.Body>
                  </Card.Root>
                </Link>
              ))}
          </Box>
          {meta && <About meta={meta} />}
        </div>
        {meta && <Footer meta={meta} />}
      </>
    );
  } catch (_e) {
    return (
      <p>
        エラー：データの取得に失敗しました
        <br />
        Error: fetch failed to {process.env.NEXT_PUBLIC_API_BASEPATH}.
      </p>
    );
  }
}
