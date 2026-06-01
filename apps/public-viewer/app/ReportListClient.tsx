"use client";

/**
 * Standalone (Windows embeddable) 用のレポート一覧（クライアント描画版）。
 *
 * ホスト版の一覧はサーバコンポーネントがビルド時に /reports を取得して描画するが、
 * スタンドアロンでは実行時に作成されたレポートを表示する必要があるため、
 * クライアントで実行時に取得し、各レポートへ /report?slug=... でリンクする。
 */

import { ApiConnectionError } from "@/components/ApiConnectionError";
import { Footer } from "@/components/Footer";
import { Header } from "@/components/Header";
import { ReporterClient } from "@/components/reporter/ReporterClient";
import type { Meta, Report } from "@/type";
import { Box, Card, Center, HStack, Heading, Image, Spinner, Text, VStack } from "@chakra-ui/react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { getApiBaseUrl } from "./utils/api";
import { getRelativeUrl } from "./utils/image-src";
import { isStandaloneBuild } from "./utils/static-build";

// Standalone is same-origin; use root-relative fetches (ignore NEXT_PUBLIC_API_BASEPATH).
const apiBase = () => (isStandaloneBuild() ? "" : getApiBaseUrl());

type LoadState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "ready"; meta: Meta; reports: Report[] };

export function ReportListClient() {
  const [state, setState] = useState<LoadState>({ status: "loading" });

  useEffect(() => {
    const base = apiBase();
    const apiKey = process.env.NEXT_PUBLIC_PUBLIC_API_KEY || "";
    let cancelled = false;

    (async () => {
      try {
        const [metaRes, reportsRes] = await Promise.all([
          fetch(`${base}/meta/metadata.json`),
          fetch(`${base}/reports`, {
            headers: { "x-api-key": apiKey, "Content-Type": "application/json" },
          }),
        ]);
        if (!metaRes.ok || !reportsRes.ok) {
          throw new Error(`一覧の取得に失敗しました (meta: ${metaRes.status}, reports: ${reportsRes.status})`);
        }
        const meta: Meta = await metaRes.json();
        const reports: Report[] = await reportsRes.json();
        if (!cancelled) setState({ status: "ready", meta, reports });
      } catch (e) {
        if (!cancelled) setState({ status: "error", message: e instanceof Error ? e.message : String(e) });
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  if (state.status === "loading") {
    return (
      <Center minH="60vh">
        <VStack>
          <Spinner size="lg" />
          <Text mt={4}>レポート一覧を読み込んでいます...</Text>
        </VStack>
      </Center>
    );
  }

  if (state.status === "error") {
    return <ApiConnectionError apiUrl={apiBase()} errorMessage={state.message} isServerSide={false} />;
  }

  const { meta, reports } = state;
  return (
    <>
      <Header />
      <Box className="container">
        <Box mx={"auto"} maxW={"1024px"} mb={10} mt="8">
          <Box mb="12">
            <ReporterClient meta={meta} apiBase={apiBase()} />
          </Box>
          <Heading textAlign={"left"} fontSize={"xl"} mb={8}>
            レポート一覧
          </Heading>
          {reports.length === 0 ? (
            <EmptyState />
          ) : (
            reports.map((report) => (
              <Link key={report.slug} href={`/report?slug=${encodeURIComponent(report.slug)}`}>
                <Card.Root
                  size="md"
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
      </Box>
      <Footer meta={meta} />
    </>
  );
}

const EmptyState = () => {
  return (
    <VStack mt={8} mb={12} gap={0} lineHeight={2}>
      <Text fontSize="18px" fontWeight="bold">
        レポートが0件です
      </Text>
      <Text fontSize="14px" textAlign={{ md: "center" }} mt={5}>
        管理画面でレポートを作成すると、ここに一覧が表示されます。
      </Text>
      <Image src={getRelativeUrl("/images/report-empty.png")} mt={8} />
    </VStack>
  );
};
