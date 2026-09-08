import { Footer } from "@/components/Footer";
import { Header } from "@/components/Header";
import { ReportListContent } from "@/components/report/ReportListContent";
import type { Meta, Report } from "@/type";
import { Box, Heading } from "@chakra-ui/react";
import type { ReactNode } from "react";

/**
 * レポート一覧の画面。
 *
 * サーバー側で組み立てる `app/page.tsx` と、shell ビルドで実行時に
 * 組み立てる `ReportListShell` の両方から使う。
 */
export function ReportListView({
  reports,
  meta,
  reporter,
}: {
  reports: Report[];
  meta: Meta;
  reporter: ReactNode;
}) {
  return (
    <>
      <Header />
      <Box className="container">
        <Box mx={"auto"} maxW={"1024px"} mb={10} mt="8">
          <Box mb="12">{reporter}</Box>
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
