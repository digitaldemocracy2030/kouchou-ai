import { Footer } from "@/components/Footer";
import { Header } from "@/components/Header";
import { Reporter } from "@/components/reporter/Reporter";
import type { Meta, Report } from "@/type";
import { Box, Card, HStack, Heading, Image, Text, VStack } from "@chakra-ui/react";
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
        <div className={"container"}>
          <Header />
          <Box mx={"auto"} maxW={"1024px"} mb={10}>
            <Box mb="12">
              <Reporter meta={meta} />
            </Box>
            <Heading textAlign={"left"} fontSize={"xl"} mb={8}>
              レポート一覧
            </Heading>
            {reports.length === 0 ? (
              <EmptyState />
            ) : (
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
                            <Text fontSize={"lg"} color={"#2577b1"} mb={1} lineClamp="2">
                              {report.title}
                            </Text>
                          </Card.Title>
                          {report.createdAt && (
                            <Text fontSize={"xs"} color={"gray.500"} mb={1}>
                              作成日時: {new Date(report.createdAt).toLocaleString("ja-JP", { timeZone: "Asia/Tokyo" })}
                            </Text>
                          )}
                          <Card.Description lineClamp={{ base: 3, md: 2 }}>{report.description || ""}</Card.Description>
                        </Box>
                      </HStack>
                    </Card.Body>
                  </Card.Root>
                </Link>
              ))
            )}
          </Box>
        </div>
        <Footer meta={meta} />
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

const EmptyState = () => {
  return (
    <VStack mt={8} mb={12} gap={0} lineHeight={2}>
      <Text fontSize="18px" fontWeight="bold">
        レポートが0件です
      </Text>
      <Text fontSize="14px" textAlign={{ md: "center" }} mt={5}>
        レポート作成が完了し公開されると、ここに一覧が表示されます。
        <Box as="br" display={{ base: "none", md: "block" }} />
        レポートが公開されるまでしばらくお待ちください。
      </Text>
      <Image src="images/report-empty.png" mt={8} />
    </VStack>
  );
};
