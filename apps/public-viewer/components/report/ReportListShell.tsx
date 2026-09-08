"use client";

import { fetchShellJson, getShellMetaUrl, getShellReportListUrl } from "@/app/utils/shell-data";
import { ReportListView } from "@/components/report/ReportListView";
import { ShellDataError } from "@/components/report/ShellDataError";
import { ShellReporter } from "@/components/reporter/ShellReporter";
import type { Meta, Report } from "@/type";
import { Box, Spinner } from "@chakra-ui/react";
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

        if (!meta) {
          throw new Error(`同梱データが見つかりませんでした (404): ${metaUrl}`);
        }

        if (!reports) {
          throw new Error(`同梱データが見つかりませんでした (404): ${listUrl}`);
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
    return <ShellDataError url={state.url} message={state.message} />;
  }

  return (
    <ReportListView reports={state.reports} meta={state.meta} reporter={<ShellReporter meta={state.meta} />} />
  );
}
