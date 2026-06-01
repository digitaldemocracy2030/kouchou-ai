"use client";

/**
 * Standalone (Windows embeddable) 用のレポート表示ページ。
 *
 * 静的エクスポートでは実行時に作成されたレポートの slug を焼き込めないため、
 * このページは静的に1ファイルだけ生成され、`?slug=...` を実行時に読んで API から取得する。
 * 一覧ページ(ReportListClient)が /report?slug=... へリンクする。
 *
 * ReportView は ssr:false でクライアント専用描画にし、ハイドレーション不一致を避ける。
 */

import { Center, Spinner } from "@chakra-ui/react";
import dynamic from "next/dynamic";
import { useEffect, useState } from "react";

const ReportView = dynamic(() => import("@/components/report/ReportView").then((m) => m.ReportView), {
  ssr: false,
  loading: () => (
    <Center minH="60vh">
      <Spinner size="lg" />
    </Center>
  ),
});

export default function StandaloneReportPage() {
  const [slug, setSlug] = useState<string | null>(null);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    setSlug(params.get("slug"));
  }, []);

  return <ReportView slug={slug} />;
}
