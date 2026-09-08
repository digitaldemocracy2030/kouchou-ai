"use client";

import { fetchShellJson, getShellMetaUrl, getShellReportListUrl } from "@/app/utils/shell-data";
import { ApiConnectionError } from "@/components/ApiConnectionError";
import { Footer } from "@/components/Footer";
import { Header } from "@/components/Header";
import { ReportListContent } from "@/components/report/ReportListContent";
import { ShellReporter } from "@/components/reporter/ShellReporter";
import type { Meta, Report } from "@/type";
import { Box, Heading, Spinner } from "@chakra-ui/react";
import { useEffect, useState } from "react";

type ShellListState =
  | { status: "loading" }
  | { status: "ready"; meta: Meta; reports: Report[] }
  | { status: "error"; url: string; message: string };

/**
 * shell ビルド用のレポート一覧。
 *
 * `app/page.tsx` と同じ画面を、同梱された静的 JSON から実行時に組み立てる。
 */
export function ReportListShell() {
  const [state, setState] = useState<ShellListState>({ status: "loading" });

  useEffect(() => {
    let active = true;
    const metaUrl = getShellMetaUrl();
    const listUrl = getShellReportListUrl();

    (async () => {
      try {
        const [meta, reports] = await Promise.all([
          fetchShellJson<Meta>(metaUrl),
          fetchShellJson<Report[]>(listUrl),
        ]);

        if (!active) return;

        if (!meta || !reports) {
          throw new Error("同梱データ (data/metadata.json, data/reports.json) が見つかりませんでした");
        }

        setState({ status: "ready", meta, reports });
      } catch (e) {
        if (!active) return;
        setState({
          status: "error",
          url: listUrl,
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
      <Box className="container" textAlign="center" py={24}>
        <Spinner />
      </Box>
    );
  }

  if (state.status === "error") {
    return <ApiConnectionError apiUrl={state.url} errorMessage={state.message} isServerSide={false} />;
  }

  const { meta, reports } = state;

  return (
    <>
      <Header />
      <Box className="container">
        <Box mx={"auto"} maxW={"1024px"} mb={10} mt="8">
          <Box mb="12">
            <ShellReporter meta={meta} />
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
}
