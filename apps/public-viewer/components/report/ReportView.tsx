import { Footer } from "@/components/Footer";
import { Header } from "@/components/Header";
import { LocalizedReportView } from "@/components/report/LocalizedReportView";
import { LanguageProvider } from "@/lib/i18n/LanguageContext";
import type { Meta, Result } from "@/type";
import type { ReactNode } from "react";

/**
 * レポート詳細の画面。
 *
 * サーバー側で組み立てる `app/[slug]/page.tsx` と、shell ビルドで実行時に
 * 組み立てる `ReportShell` の両方から使う。レポーターの表示だけが
 * 取得方法によって異なるので slot で受ける。
 *
 * 表示言語（日本語 / 英語 / 韓国語）は LanguageProvider が持ち、本文の
 * 差し替えと UI 文言の切替は LocalizedReportView 以下で行う。
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
    <LanguageProvider>
      <Header />
      <LocalizedReportView result={result} reporter={reporter} />
      <Footer meta={meta} />
    </LanguageProvider>
  );
}
