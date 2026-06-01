"use client";

/**
 * Standalone 一覧ページのクライアント専用ラッパ。
 *
 * 静的エクスポートでは "use client" ページも一度 SSR(prerender)されるため、Chakra/emotion を
 * 含む動的な一覧をサーバ描画するとハイドレーション不一致(React #418)で落ちる。ssr:false で
 * クライアント描画のみにして不一致を回避する。
 */

import { Center, Spinner } from "@chakra-ui/react";
import dynamic from "next/dynamic";

const ReportListClient = dynamic(() => import("./ReportListClient").then((m) => m.ReportListClient), {
  ssr: false,
  loading: () => (
    <Center minH="60vh">
      <Spinner size="lg" />
    </Center>
  ),
});

export function StandaloneListPage() {
  return <ReportListClient />;
}
