"use client";

/**
 * 実行時に slug を受け取り、API からレポートを取得して描画するクライアントコンポーネント。
 *
 * Standalone (Windows embeddable) ビルドで使用する。ホスト版の /[slug] は
 * サーバ側でデータを焼き込むが、スタンドアロンでは実行時生成レポートを表示するため
 * クライアントで取得する。/report?slug=... と [slug] の standalone 分岐の両方から利用する。
 */

import { ApiConnectionError } from "@/components/ApiConnectionError";
import { Footer } from "@/components/Footer";
import { Header } from "@/components/Header";
import { Analysis } from "@/components/report/Analysis";
import { BackButton } from "@/components/report/BackButton";
import { ClientContainer } from "@/components/report/ClientContainer";
import { Overview } from "@/components/report/Overview";
import { ReporterClient } from "@/components/reporter/ReporterClient";
import { getApiBaseUrl } from "@/app/utils/api";
import { isStandaloneBuild } from "@/app/utils/static-build";
import type { Meta, Result } from "@/type";

// Standalone is served same-origin by FastAPI, so use root-relative fetches and
// ignore NEXT_PUBLIC_API_BASEPATH (which a dev .env.local may point elsewhere).
const apiBase = () => (isStandaloneBuild() ? "" : getApiBaseUrl());
import { Box, Center, Separator, Spinner, Text, VStack } from "@chakra-ui/react";
import { useEffect, useState } from "react";

type LoadState =
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "notfound" }
  | { status: "ready"; meta: Meta; result: Result };

export function ReportView({ slug }: { slug: string | null }) {
  const [state, setState] = useState<LoadState>({ status: "loading" });

  useEffect(() => {
    if (!slug) {
      setState({ status: "notfound" });
      return;
    }

    const base = apiBase();
    const apiKey = process.env.NEXT_PUBLIC_PUBLIC_API_KEY || "";
    let cancelled = false;

    (async () => {
      try {
        const [metaRes, resultRes] = await Promise.all([
          fetch(`${base}/meta/metadata.json`),
          fetch(`${base}/reports/${slug}`, {
            headers: { "x-api-key": apiKey, "Content-Type": "application/json" },
          }),
        ]);

        if (metaRes.status === 404 || resultRes.status === 404) {
          if (!cancelled) setState({ status: "notfound" });
          return;
        }
        if (!metaRes.ok || !resultRes.ok) {
          throw new Error(`レポートの取得に失敗しました (meta: ${metaRes.status}, report: ${resultRes.status})`);
        }

        const meta: Meta = await metaRes.json();
        const result: Result = await resultRes.json();
        if (!cancelled) setState({ status: "ready", meta, result });
      } catch (e) {
        if (!cancelled) setState({ status: "error", message: e instanceof Error ? e.message : String(e) });
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [slug]);

  if (state.status === "loading") {
    return (
      <Center minH="60vh">
        <VStack>
          <Spinner size="lg" />
          <Text mt={4}>レポートを読み込んでいます...</Text>
        </VStack>
      </Center>
    );
  }

  if (state.status === "error") {
    return <ApiConnectionError apiUrl={apiBase()} errorMessage={state.message} isServerSide={false} />;
  }

  if (state.status === "notfound") {
    return (
      <Center minH="60vh">
        <VStack>
          <Text fontSize="18px" fontWeight="bold">
            レポートが見つかりませんでした
          </Text>
          <BackButton />
        </VStack>
      </Center>
    );
  }

  const { meta, result } = state;
  return (
    <>
      <Header />
      <Box className="container" mt="8">
        <Overview result={result} />
        <ClientContainer result={result} />
        <Analysis result={result} />
        <BackButton />
        <Separator my={12} maxW={"750px"} mx={"auto"} />
        <Box maxW={"750px"} mx={"auto"} mb={24}>
          <ReporterClient meta={meta} apiBase={apiBase()} />
        </Box>
      </Box>
      <Footer meta={meta} />
    </>
  );
}
