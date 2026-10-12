import "@testing-library/jest-dom";
import { Provider } from "@/components/ui/provider";
import type { Result } from "@/type";
import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import fixture from "../dev/viewer-fixture.json";
import { ClientContainer } from "./ClientContainer";

// jsdom には structuredClone が無く、Chakra v3 の recipe 処理が必要とするため補う
globalThis.structuredClone ??= <T,>(value: T): T => (value === undefined ? value : JSON.parse(JSON.stringify(value)));

// lucide-react は ESM のみ配布で Jest が変換しないため、全アイコンを空コンポーネントにする
jest.mock("lucide-react", () => new Proxy({}, { get: (_, name) => (name === "__esModule" ? true : () => null) }));

// Plotly を読み込まず、散布図に渡された階層だけを記録する
jest.mock("@/components/charts/ScatterChart", () => ({
  ScatterChart: (props: { targetLevel: number }) => <div data-testid="scatter" data-level={props.targetLevel} />,
}));
jest.mock("@/components/charts/TreemapChart", () => ({
  TreemapChart: () => <div data-testid="treemap" />,
}));
jest.mock("@/components/charts/HierarchyListChart", () => ({
  HierarchyListChart: () => <div data-testid="hierarchy-list" />,
}));
jest.mock("@/components/icons/ViewIcons", () => ({
  AllViewIcon: () => null,
  DenseViewIcon: () => null,
  DetailViewIcon: () => null,
  HierarchyViewIcon: () => null,
  ListViewIcon: () => null,
}));

beforeAll(() => {
  // Chakra の Dialog（zag.js）は ResizeObserver を要求する（jsdom には無い）
  class ResizeObserverStub {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  Object.defineProperty(window, "ResizeObserver", { writable: true, value: ResizeObserverStub });
  // ClientContainer は狭い画面の判定に matchMedia を使う（jsdom には無い）
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: (query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: jest.fn(),
      removeListener: jest.fn(),
      addEventListener: jest.fn(),
      removeEventListener: jest.fn(),
      dispatchEvent: jest.fn(),
    }),
  });
});

/**
 * zag.js（SegmentGroup / Dialog）が requestAnimationFrame 後に行う状態更新と
 * dismiss 層の登録・解除を act 内で流す（jsdom の rAF は約16ms後に発火する）
 */
async function flush() {
  await act(async () => {
    await new Promise((resolve) => setTimeout(resolve, 50));
  });
}

async function renderViewer() {
  const result = structuredClone(fixture) as unknown as Result;
  const utils = render(
    <Provider>
      <ClientContainer result={result} />
    </Provider>,
  );
  await flush();
  return utils;
}

describe("全画面表示でのクラスタ粒度の切替", () => {
  it("全画面のまま大きいクラスタと細かいクラスタを行き来し、全画面終了も使える", async () => {
    await renderViewer();
    const deepest = Math.max(...fixture.clusters.map((c) => c.level));
    expect(screen.getByTestId("scatter")).toHaveAttribute("data-level", "1");

    fireEvent.click(screen.getByRole("button", { name: "全画面表示" }));
    const dialog = screen.getByRole("dialog");
    expect(within(dialog).getByTestId("scatter")).toHaveAttribute("data-level", "1");

    // 細かいクラスタへ
    fireEvent.click(within(dialog).getByRole("button", { name: "詳細クラスタ" }));
    expect(screen.getByRole("dialog")).toBe(dialog); // 全画面のまま
    expect(within(dialog).getByTestId("scatter")).toHaveAttribute("data-level", String(deepest));
    expect(within(dialog).getByRole("button", { name: "詳細クラスタ" })).toHaveAttribute("aria-pressed", "true");

    // 大きいクラスタへ戻す
    fireEvent.click(within(dialog).getByRole("button", { name: "全体" }));
    expect(screen.getByRole("dialog")).toBe(dialog);
    expect(within(dialog).getByTestId("scatter")).toHaveAttribute("data-level", "1");

    // 全画面終了は従来どおり動く
    fireEvent.click(within(dialog).getByRole("button", { name: "全画面終了" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    // 全画面を抜けた後も、通常表示は全画面中に選んだ粒度を引き継ぐ
    expect(screen.getByTestId("scatter")).toHaveAttribute("data-level", "1");
    await flush();
  });

  it("全画面中に切り替えた粒度は、全画面を抜けた後の通常表示にも反映される", async () => {
    await renderViewer();
    const deepest = Math.max(...fixture.clusters.map((c) => c.level));
    fireEvent.click(screen.getByRole("button", { name: "全画面表示" }));
    const dialog = screen.getByRole("dialog");
    fireEvent.click(within(dialog).getByRole("button", { name: "詳細クラスタ" }));
    fireEvent.click(within(dialog).getByRole("button", { name: "全画面終了" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(screen.getByTestId("scatter")).toHaveAttribute("data-level", String(deepest));
    await flush();
  });

  it("Escape キーで全画面を終了できる", async () => {
    await renderViewer();
    fireEvent.click(screen.getByRole("button", { name: "全画面表示" }));
    await screen.findByRole("dialog");
    // zag.js の dismiss 層は開いた後に rAF で document へ keydown を登録する
    await flush();
    fireEvent.keyDown(document, { key: "Escape" });
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    await flush();
  });
});
