"use client";

import { getBasePath } from "@/app/utils/image-src";
import {
  ShellDataFetchError,
  fetchShellJson,
  getShellMetaUrl,
  getShellReportUrl,
  resolveShellSlug,
} from "@/app/utils/shell-data";
import { Footer } from "@/components/Footer";
import { Header } from "@/components/Header";
import { ReportView } from "@/components/report/ReportView";
import { ShellDataError } from "@/components/report/ShellDataError";
import { ShellReporter } from "@/components/reporter/ShellReporter";
import type { Meta, Result } from "@/type";
import { Box, Button, Spinner, Text } from "@chakra-ui/react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

type ShellState =
  | { status: "loading" }
  | { status: "ready"; meta: Meta; result: Result }
  | { status: "notFound"; meta: Meta | null }
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
  const pathname = usePathname();
  const [state, setState] = useState<ShellState>({ status: "loading" });

  useEffect(() => {
    let active = true;
    const slug = resolveShellSlug(pathname, getBasePath());

    if (!slug) {
      setState({ status: "notFound", meta: null });
      return;
    }

    setState({ status: "loading" });

    const metaUrl = getShellMetaUrl();
    const reportUrl = getShellReportUrl(slug);

    (async () => {
      try {
        const [meta, result] = await Promise.all([
          fetchShellJson<Meta>(metaUrl),
          fetchShellJson<Result>(reportUrl),
        ]);

        if (!active) return;

        // メタデータの欠落は配布物の組み立て漏れ。レポートの欠落と混同しない。
        if (!meta) {
          setState({
            status: "error",
            url: metaUrl,
            message: "同梱データが見つかりませんでした (404)",
          });
          return;
        }

        if (!result) {
          setState({ status: "notFound", meta });
          return;
        }

        setState({ status: "ready", meta, result });
      } catch (e) {
        if (!active) return;
        // 失敗したファイルをそのまま出す（別のファイルを指すと調査を誤らせる）
        setState({
          status: "error",
          url: e instanceof ShellDataFetchError ? e.url : reportUrl,
          message: e instanceof Error ? e.message : String(e),
        });
      }
    })();

    return () => {
      active = false;
    };
  }, [pathname]);

  if (state.status === "loading") {
    return (
      <Box className="container" mt="8" textAlign="center" py={24}>
        <Spinner />
      </Box>
    );
  }

  if (state.status === "error") {
    return <ShellDataError url={state.url} message={state.message} />;
  }

  if (state.status === "notFound") {
    // 素の文言だけだとサイトの体裁から浮くので、他の画面と同じ枠に収める
    return (
      <>
        <Header />
        <Box className="container" mt="8" textAlign="center" py={24}>
          <Text mb={6}>ページが見つかりませんでした</Text>
          <Link href="/">
            <Button>トップに戻る</Button>
          </Link>
        </Box>
        {state.meta ? <Footer meta={state.meta} /> : null}
      </>
    );
  }

  return (
    <ReportView result={state.result} meta={state.meta} reporter={<ShellReporter meta={state.meta} />} />
  );
}
