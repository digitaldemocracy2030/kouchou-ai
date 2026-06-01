"use client";

/**
 * Standalone (Windows embeddable) 用の admin ルートページ（クライアント描画版）。
 *
 * ホスト版 (app/page.tsx) はサーバコンポーネントが /admin/reports を SSR で取得するが、
 * 静的エクスポートではサーバが無いため、ビルド時に scripts/standalone-prep.mjs が
 * このファイルを app/page.tsx に差し替える。実行時にクライアントから取得して描画する。
 */

import { Header } from "@/components/Header";
import type { Report } from "@/type";
import { Box, Center, Code, Heading, Spinner, Text, VStack } from "@chakra-ui/react";
import { useEffect, useState } from "react";
import { PageContent } from "./_components/PageContent";
import { getApiBaseUrl } from "./utils/api";

type LoadState =
  | { status: "loading" }
  | { status: "error"; title: string; description: string; details?: string }
  | { status: "ready"; reports: Report[] };

export default function Page() {
  const [state, setState] = useState<LoadState>({ status: "loading" });

  useEffect(() => {
    const apiUrl = getApiBaseUrl();
    let cancelled = false;

    (async () => {
      try {
        const res = await fetch(`${apiUrl}/admin/reports`, {
          headers: {
            "x-api-key": process.env.NEXT_PUBLIC_ADMIN_API_KEY || "",
            "Content-Type": "application/json",
          },
        });
        if (!res.ok) {
          if (!cancelled)
            setState({
              status: "error",
              title: "レポートの取得に失敗しました",
              description:
                res.status === 401
                  ? "APIキーが無効か未設定です（ADMIN_API_KEY / NEXT_PUBLIC_ADMIN_API_KEY を確認）。"
                  : `HTTPステータス: ${res.status}`,
              details: `接続先: ${apiUrl}/admin/reports`,
            });
          return;
        }
        const reports: Report[] = await res.json();
        if (!cancelled) setState({ status: "ready", reports });
      } catch (e) {
        if (!cancelled)
          setState({
            status: "error",
            title: "APIサーバーに接続できません",
            description: "APIサーバーが起動していない可能性があります。",
            details: e instanceof Error ? e.message : String(e),
          });
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <Box className="container" bgColor="bg.secondary">
      <Header />
      {state.status === "loading" && (
        <Center minH="60vh">
          <VStack>
            <Spinner size="lg" />
            <Text mt={4}>レポート一覧を読み込んでいます...</Text>
          </VStack>
        </Center>
      )}
      {state.status === "error" && (
        <Box mx="auto" maxW="600px" px="6" py="12">
          <VStack gap={4} align="stretch">
            <Heading textAlign="center" fontSize="xl" color="red.600">
              {state.title}
            </Heading>
            <Text textAlign="center" color="gray.600">
              {state.description}
            </Text>
            {state.details && (
              <Code p={3} borderRadius="md" fontSize="sm" display="block" whiteSpace="pre-wrap">
                {state.details}
              </Code>
            )}
          </VStack>
        </Box>
      )}
      {state.status === "ready" && (
        <Box mx="auto" maxW="1024px" boxSizing="content-box" px="6" py="12">
          <PageContent reports={state.reports} />
        </Box>
      )}
    </Box>
  );
}
