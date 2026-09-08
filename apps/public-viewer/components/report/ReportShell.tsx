"use client";

import { getBasePath } from "@/app/utils/image-src";
import { fetchShellJson, getShellMetaUrl, getShellReportUrl, resolveShellSlug } from "@/app/utils/shell-data";
import { ApiConnectionError } from "@/components/ApiConnectionError";
import { Footer } from "@/components/Footer";
import { Header } from "@/components/Header";
import { Analysis } from "@/components/report/Analysis";
import { BackButton } from "@/components/report/BackButton";
import { ClientContainer } from "@/components/report/ClientContainer";
import { Overview } from "@/components/report/Overview";
import { ReadingGuide } from "@/components/report/ReadingGuide";
import { ShellReporter } from "@/components/reporter/ShellReporter";
import type { Meta, Result } from "@/type";
import { Box, Separator, Spinner, Text } from "@chakra-ui/react";
import Link from "next/link";
import { useEffect, useState } from "react";

type ShellState =
  | { status: "loading" }
  | { status: "ready"; meta: Meta; result: Result }
  | { status: "notFound" }
  | { status: "error"; url: string; message: string };

/**
 * shell ビルド用のレポート表示。
 *
 * サーバー側でレポートを埋め込む `app/[slug]/page.tsx` と同じ画面を、
 * 同梱された静的 JSON から実行時に組み立てる。表示するレポートは
 * build 時の params ではなく URL から決める（1 枚の HTML を各 slug へ
 * コピーして配布するため）。
 */
export function ReportShell() {
  const [state, setState] = useState<ShellState>({ status: "loading" });

  useEffect(() => {
    let active = true;
    const slug = resolveShellSlug(window.location.pathname, getBasePath());

    if (!slug) {
      setState({ status: "notFound" });
      return;
    }

    const metaUrl = getShellMetaUrl();
    const reportUrl = getShellReportUrl(slug);

    (async () => {
      try {
        const [meta, result] = await Promise.all([
          fetchShellJson<Meta>(metaUrl),
          fetchShellJson<Result>(reportUrl),
        ]);

        if (!active) return;

        if (!meta || !result) {
          setState({ status: "notFound" });
          return;
        }

        setState({ status: "ready", meta, result });
      } catch (e) {
        if (!active) return;
        setState({
          status: "error",
          url: reportUrl,
          message: e instanceof Error ? e.message : String(e),
        });
      }
    })();

    return () => {
      active = false;
    };
  }, []);

  if (state.status === "loading") {
    return (
      <Box className="container" mt="8" textAlign="center" py={24}>
        <Spinner />
      </Box>
    );
  }

  if (state.status === "error") {
    return <ApiConnectionError apiUrl={state.url} errorMessage={state.message} isServerSide={false} />;
  }

  if (state.status === "notFound") {
    return (
      <Box className="container" mt="8" textAlign="center" py={24}>
        <Text mb={4}>ページが見つかりませんでした</Text>
        <Link href="/">トップに戻る</Link>
      </Box>
    );
  }

  const { meta, result } = state;

  return (
    <>
      <Header />
      <Box className="container" mt="8">
        <Overview result={result} />
        <ReadingGuide />
        <ClientContainer result={result} />
        <Analysis result={result} />
        <BackButton />
        <Separator my={12} maxW={"750px"} mx={"auto"} />
        <Box maxW={"750px"} mx={"auto"} mb={24}>
          <ShellReporter meta={meta} />
        </Box>
      </Box>
      <Footer meta={meta} />
    </>
  );
}
