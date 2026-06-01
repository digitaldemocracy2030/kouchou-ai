"use client";

/**
 * Standalone ビルドで [slug] ルートを output:export に通すための薄いクライアントラッパ。
 *
 * standalone では [slug] のページは実際には使わず（一覧は /report?slug=... へリンクする）、
 * export を成立させるための sentinel を1つだけ生成する。万一このルートが配信された場合に
 * 備え、パス末尾の slug を読んで実行時取得する ReportView を描画しておく。
 */

import { Center, Spinner } from "@chakra-ui/react";
import dynamic from "next/dynamic";
import { usePathname } from "next/navigation";

const ReportView = dynamic(() => import("@/components/report/ReportView").then((m) => m.ReportView), {
  ssr: false,
  loading: () => (
    <Center minH="60vh">
      <Spinner size="lg" />
    </Center>
  ),
});

export function StandaloneSlugView() {
  const pathname = usePathname() || "";
  const segments = pathname.split("/").filter(Boolean);
  const slug = segments.length > 0 ? decodeURIComponent(segments[segments.length - 1]) : null;
  return <ReportView slug={slug} />;
}
