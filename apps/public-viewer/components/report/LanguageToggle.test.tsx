import "@testing-library/jest-dom";
import { Provider } from "@/components/ui/provider";
import { LanguageProvider, useLanguage, useLocalizedResult } from "@/lib/i18n/LanguageContext";
import type { Result } from "@/type";
import { act, fireEvent, render, screen } from "@testing-library/react";
import { LanguageToggle } from "./LanguageToggle";

const result = {
  arguments: [],
  clusters: [
    { level: 1, id: "1", label: "交通", takeaway: "交通の説明", value: 1, parent: "0", density_rank_percentile: 0 },
  ],
  comments: {},
  propertyMap: {},
  translations: { en: { clusters: { "1": { label: "Transport" } } } },
  overview: "概要",
  config: { question: "問い", intro: "" },
  comment_num: 1,
} as unknown as Result;

function Consumer() {
  const { messages, language } = useLanguage();
  const localized = useLocalizedResult(result);
  return (
    <>
      <h1>{messages.report}</h1>
      <p data-testid="lang">{language}</p>
      <p data-testid="label">{localized.clusters[0].label}</p>
    </>
  );
}

function renderToggle() {
  return render(
    <Provider>
      <LanguageProvider>
        <LanguageToggle />
        <Consumer />
      </LanguageProvider>
    </Provider>,
  );
}

beforeEach(() => {
  window.localStorage.clear();
  window.history.replaceState(null, "", "/report-1");
});

it("既定は日本語で、切り替えると UI 文言と本文が変わり選択が保存される", () => {
  renderToggle();
  expect(screen.getByRole("heading", { name: "レポート" })).toBeInTheDocument();
  expect(screen.getByTestId("label")).toHaveTextContent("交通");
  expect(screen.getByRole("button", { name: "日本語" })).toHaveAttribute("aria-pressed", "true");

  fireEvent.click(screen.getByRole("button", { name: "English" }));

  expect(screen.getByRole("heading", { name: "Report" })).toBeInTheDocument();
  expect(screen.getByTestId("label")).toHaveTextContent("Transport");
  expect(screen.getByRole("button", { name: "English" })).toHaveAttribute("aria-pressed", "true");
  expect(window.localStorage.getItem("kouchou-ai.language")).toBe("en");
  expect(window.location.search).toBe("?lang=en");
  expect(document.documentElement.lang).toBe("en");

  // 韓国語の翻訳は無いので本文は元の言語のまま、UI 文言だけ変わる
  fireEvent.click(screen.getByRole("button", { name: "한국어" }));
  expect(screen.getByRole("heading", { name: "보고서" })).toBeInTheDocument();
  expect(screen.getByTestId("label")).toHaveTextContent("交通");

  // 日本語に戻すとクエリは消える
  fireEvent.click(screen.getByRole("button", { name: "日本語" }));
  expect(window.location.search).toBe("");
});

it("URL の ?lang= を初期言語にする（共有リンク・shell 配布物向け）", async () => {
  window.history.replaceState(null, "", "/report-1?lang=ko");
  await act(async () => {
    renderToggle();
  });
  expect(screen.getByTestId("lang")).toHaveTextContent("ko");
  expect(screen.getByRole("button", { name: "한국어" })).toHaveAttribute("aria-pressed", "true");
});

it("Provider が無くても日本語で描画できる（テスト・開発用カタログ向け）", () => {
  render(
    <Provider>
      <LanguageToggle />
      <Consumer />
    </Provider>,
  );
  expect(screen.getByRole("heading", { name: "レポート" })).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "English" }));
  expect(screen.getByRole("heading", { name: "レポート" })).toBeInTheDocument();
});
