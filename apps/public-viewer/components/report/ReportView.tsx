import { Footer } from "@/components/Footer";
import { Header } from "@/components/Header";
import { Analysis } from "@/components/report/Analysis";
import { BackButton } from "@/components/report/BackButton";
import { ClientContainer } from "@/components/report/ClientContainer";
import { Overview } from "@/components/report/Overview";
import { ReadingGuide } from "@/components/report/ReadingGuide";
import type { Meta, Result } from "@/type";
import { Box, Separator } from "@chakra-ui/react";
import type { ReactNode } from "react";

/**
 * レポート詳細の画面。
 *
 * サーバー側で組み立てる `app/[slug]/page.tsx` と、shell ビルドで実行時に
 * 組み立てる `ReportShell` の両方から使う。レポーターの表示だけが
 * 取得方法によって異なるので slot で受ける。
 */
export function ReportView({
  result,
  meta,
  reporter,
}: {
  result: Result;
  meta: Meta;
  reporter: ReactNode;
}) {
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
          {reporter}
        </Box>
      </Box>
      <Footer meta={meta} />
    </>
  );
}
