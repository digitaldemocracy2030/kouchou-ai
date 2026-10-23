import "@testing-library/jest-dom";
import { Provider } from "@/components/ui/provider";
import type { Result } from "@/type";
import { act, fireEvent, render, screen, within } from "@testing-library/react";
import fixture from "../dev/viewer-fixture.json";
import { ClientContainer } from "./ClientContainer";

// jsdom には structuredClone が無く、Chakra v3 の recipe 処理が必要とするため補う
globalThis.structuredClone ??= <T,>(value: T): T => (value === undefined ? value : JSON.parse(JSON.stringify(value)));

// lucide-react は ESM のみ配布で Jest が変換しないため、全アイコンを空コンポーネントにする
jest.mock("lucide-react", () => new Proxy({}, { get: (_, name) => (name === "__esModule" ? true : () => null) }));

// Plotly を読み込まず、散布図のクラスタ選択（onSelectCluster）をボタンで擬似的に発火させる
jest.mock("@/components/charts/ScatterChart", () => ({
  ScatterChart: (props: { targetLevel: number; onSelectCluster?: (id: string) => void }) => (
    <div data-testid="scatter" data-level={props.targetLevel}>
      <button type="button" onClick={() => props.onSelectCluster?.("1_1")}>
        クラスタ1_1を選択
      </button>
    </div>
  ),
}));
jest.mock("@/components/charts/TreemapChart", () => ({ TreemapChart: () => <div data-testid="treemap" /> }));
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
  class ResizeObserverStub {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  Object.defineProperty(window, "ResizeObserver", { writable: true, value: ResizeObserverStub });
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
  // jsdom は scrollIntoView を実装しないため stub する（連動時にスクロールを呼ぶ）
  Element.prototype.scrollIntoView = jest.fn();
});

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

it("散布図でクラスタを選択すると、連動一覧の該当項目がハイライトされる", async () => {
  const { container } = await renderViewer();
  // 既定は散布図（scatterAll）なので連動一覧が表示される
  expect(screen.getByTestId("scatter")).toHaveAttribute("data-level", "1");
  // 選択前はハイライトされた項目は無い
  expect(container.querySelector('[aria-current="true"]')).toBeNull();

  // 散布図の点クリックを擬似発火
  fireEvent.click(screen.getByRole("button", { name: "クラスタ1_1を選択" }));

  // ハイライトされるのは選択したクラスタ（1_1）のカード 1 件だけであること
  const selected = container.querySelectorAll('[aria-current="true"]');
  expect(selected).toHaveLength(1);
  expect(selected[0].textContent).toContain("社会的影響に配慮した法案の検討と未来のルール形成");
});

it("全画面で表示モードを切り替えると散布図の選択は解除される", async () => {
  const { container } = await renderViewer();
  fireEvent.click(screen.getByRole("button", { name: "クラスタ1_1を選択" }));
  expect(container.querySelector('[aria-current="true"]')).not.toBeNull();

  // 全画面ツールバーの粒度切替（詳細クラスタ）で一覧の中身が変わるため選択は解除される
  fireEvent.click(screen.getByRole("button", { name: "全画面表示" }));
  const dialog = await screen.findByRole("dialog");
  fireEvent.click(within(dialog).getByRole("button", { name: "詳細クラスタ" }));
  await flush();
  expect(container.querySelector('[aria-current="true"]')).toBeNull();
});

it("全画面で表示モードを切り替えて全体に戻しても、散布図の選択は復活せず自動スクロールもしない", async () => {
  const { container } = await renderViewer();
  fireEvent.click(screen.getByRole("button", { name: "クラスタ1_1を選択" }));
  expect(container.querySelector('[aria-current="true"]')).not.toBeNull();
  const scrollIntoView = Element.prototype.scrollIntoView as jest.Mock;
  scrollIntoView.mockClear();

  fireEvent.click(screen.getByRole("button", { name: "全画面表示" }));
  const dialog = await screen.findByRole("dialog");
  fireEvent.click(within(dialog).getByRole("button", { name: "詳細クラスタ" }));
  await flush();
  fireEvent.click(within(dialog).getByRole("button", { name: "全体" }));
  await flush();

  expect(container.querySelector('[aria-current="true"]')).toBeNull();
  expect(scrollIntoView).not.toHaveBeenCalled();
});

it.each(["階層", "詳細クラスタ"])(
  "表示モードのタブで「%s」へ切り替えて全体に戻しても、散布図の選択は復活せず自動スクロールもしない",
  async (mode) => {
    const { container } = await renderViewer();
    fireEvent.click(screen.getByRole("button", { name: "クラスタ1_1を選択" }));
    expect(container.querySelector('[aria-current="true"]')).not.toBeNull();
    const scrollIntoView = Element.prototype.scrollIntoView as jest.Mock;
    scrollIntoView.mockClear();

    fireEvent.click(screen.getByRole("radio", { name: mode }));
    await flush();
    fireEvent.click(screen.getByRole("radio", { name: "全体" }));
    await flush();

    expect(screen.getByTestId("scatter")).toHaveAttribute("data-level", "1");
    expect(container.querySelector('[aria-current="true"]')).toBeNull();
    expect(scrollIntoView).not.toHaveBeenCalled();
  },
);
