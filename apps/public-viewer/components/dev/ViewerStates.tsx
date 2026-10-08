"use client";
import { ApiConnectionError } from "@/components/ApiConnectionError";
import { ClientContainer } from "@/components/report/ClientContainer";
import { LanguageToggle } from "@/components/report/LanguageToggle";
import { Overview } from "@/components/report/Overview";
import { ReportListContent } from "@/components/report/ReportListContent";
import { ReporterContent } from "@/components/reporter/ReporterContent";
import { LanguageProvider, useLocalizedResult } from "@/lib/i18n/LanguageContext";
import { ReportVisibility, type Result } from "@/type";
import { useState } from "react";
import fixture from "./viewer-fixture.json";

const states = [
  "通常",
  "レポート0件",
  "メタデータなし",
  "接続エラー",
  "属性なし",
  "空の意見",
  "明示的な散布図",
  "翻訳あり",
];

/** 言語切替の確認用。LLM なしで仕組みを見るため、訳文は元の文言に印を付けただけのもの。 */
function withMockTranslations(result: Result): Result {
  const mark = (prefix: string) => ({
    clusters: Object.fromEntries(
      result.clusters.map((c) => [c.id, { label: `${prefix} ${c.label}`, takeaway: `${prefix} ${c.takeaway}` }]),
    ),
    overview: `${prefix} ${result.overview}`,
    question: `${prefix} ${result.config.question}`,
  });
  return { ...result, translations: { en: mark("[EN]"), ko: mark("[KO]") } };
}

function LocalizedCatalogReport({ result }: { result: Result }) {
  const localized = useLocalizedResult(result);
  return (
    <>
      <LanguageToggle />
      <Overview result={localized} />
      <ClientContainer result={localized} />
    </>
  );
}

export function ViewerStates() {
  const [state, setState] = useState("通常");
  const meta = {
    isDefault: state === "メタデータなし",
    reporter: "確認用レポーター",
    message: "仮想アンケート由来のUI確認用データ",
    webLink: "",
  };
  let result = structuredClone(fixture) as unknown as Result;
  if (state === "属性なし") for (const arg of result.arguments) arg.attributes = {};
  if (state === "空の意見") {
    result.arguments = [];
    for (const group of result.clusters) group.value = 0;
  }
  if (state === "明示的な散布図")
    result.visualizationConfig = { version: "1", enabledCharts: ["scatterAll", "treemap"], defaultChart: "scatterAll" };
  if (state === "翻訳あり") result = withMockTranslations(result);
  return (
    <main style={{ padding: 16 }}>
      <h1>Viewer状態カタログ（開発専用）</h1>
      <label>
        状態{" "}
        <select aria-label="状態" value={state} onChange={(e) => setState(e.target.value)}>
          {states.map((s) => (
            <option key={s}>{s}</option>
          ))}
        </select>
      </label>
      <p>
        データの作成・削除やAPIキーは不要です。通常状態の属性フィルターで一致しない文字列を検索すると、絞り込み0件も確認できます。
        「翻訳あり」では言語切替で本文が差し替わること（全画面でも切り替えられること）を確認できます。
      </p>
      {state === "接続エラー" ? (
        <ApiConnectionError apiUrl="(確認用・接続しません)" errorMessage="確認用の接続失敗" />
      ) : (
        <>
          <ReporterContent meta={meta}>{null}</ReporterContent>
          <ReportListContent
            meta={meta}
            reports={
              state === "レポート0件"
                ? []
                : [
                    {
                      slug: "dev/viewer-states",
                      title: "確認用レポート",
                      description: "同じコンポーネントを状態別に確認",
                      status: "completed",
                      isPubcom: false,
                      visibility: ReportVisibility.PUBLIC,
                    },
                  ]
            }
          />
          {state === "翻訳あり" ? (
            <LanguageProvider>
              <LocalizedCatalogReport key={state} result={result} />
            </LanguageProvider>
          ) : (
            state !== "レポート0件" && <ClientContainer key={state} result={result} />
          )}
        </>
      )}
    </main>
  );
}
