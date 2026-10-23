import "@testing-library/jest-dom";
import { Provider } from "@/components/ui/provider";
import type { Meta } from "@/type";
import { render, screen } from "@testing-library/react";
import { ReporterContent } from "./ReporterContent";

// jsdom には structuredClone が無く、Chakra v3 の recipe 処理が必要とするため補う
globalThis.structuredClone ??= <T,>(value: T): T => (value === undefined ? value : JSON.parse(JSON.stringify(value)));
jest.mock("lucide-react", () => new Proxy({}, { get: (_, name) => (name === "__esModule" ? true : () => null) }));

function renderReporter(meta: Meta) {
  return render(
    <Provider>
      <ReporterContent meta={meta}>{null}</ReporterContent>
    </Provider>,
  );
}

// /meta/metadata.json は custom/metadata.json に無い項目を null で返す（apps/api/src/routers/meta.py）。
// API を経由しない静的データではキー自体が無いこともある。
describe("ReporterContent", () => {
  it("message が null でも描画でき、メッセージ欄は空になる", () => {
    const { container } = renderReporter({
      reporter: "発行者",
      message: null,
      webLink: "https://example.org/",
      isDefault: false,
    });
    expect(screen.getByText("発行者")).toBeInTheDocument();
    expect(screen.getByText("ウェブページ")).toBeInTheDocument();
    expect(container.textContent).not.toContain("null");
  });

  it("message のキーが無くても描画できる", () => {
    renderReporter({ reporter: "発行者", isDefault: false });
    expect(screen.getByText("発行者")).toBeInTheDocument();
  });

  it("reporter が null でも描画でき、メッセージは表示される", () => {
    const { container } = renderReporter({ reporter: null, message: "ご協力ありがとうございました", isDefault: false });
    expect(screen.getByText("ご協力ありがとうございました")).toBeInTheDocument();
    expect(container.textContent).not.toContain("null");
  });

  it("isDefault のときは message が null でも設定方法の案内を出す", () => {
    renderReporter({ reporter: null, message: null, isDefault: true });
    expect(screen.getByText(/レポーター情報が未設定です/)).toBeInTheDocument();
  });

  it("長いメッセージは折りたたみ、全文表示できる（従来どおり）", () => {
    renderReporter({ reporter: "発行者", message: "あ".repeat(80), isDefault: false });
    expect(screen.getByText("全文表示")).toBeInTheDocument();
  });
});
