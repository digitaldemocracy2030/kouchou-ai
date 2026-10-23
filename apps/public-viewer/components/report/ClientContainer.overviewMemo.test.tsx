import "@testing-library/jest-dom";
import { Provider } from "@/components/ui/provider";
import type { Result } from "@/type";
import { act, fireEvent, render, screen } from "@testing-library/react";
import fixture from "../dev/viewer-fixture.json";
import { ClientContainer } from "./ClientContainer";

// jsdom には structuredClone が無く、Chakra v3 の recipe 処理が必要とするため補う
globalThis.structuredClone ??= <T,>(value: T): T => (value === undefined ? value : JSON.parse(JSON.stringify(value)));

// lucide-react は ESM のみ配布で Jest が変換しないため、全アイコンを空コンポーネントにする
jest.mock("lucide-react", () => new Proxy({}, { get: (_, name) => (name === "__esModule" ? true : () => null) }));

// Plotly を読み込まず、散布図の点クリック（onSelectCluster）をボタンで擬似的に発火させる
jest.mock("@/components/charts/ScatterChart", () => ({
  ScatterChart: (props: { onSelectCluster?: (id: string) => void }) => (
    <button type="button" onClick={() => props.onSelectCluster?.("2_86")}>
      クラスタ2_86を選択
    </button>
  ),
}));
jest.mock("@/components/charts/TreemapChart", () => ({
  TreemapChart: (props: { level: string }) => <div data-testid="treemap" data-level={props.level} />,
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
  Element.prototype.scrollIntoView = jest.fn();
});

async function flush() {
  await act(async () => {
    await new Promise((resolve) => setTimeout(resolve, 50));
  });
}

/**
 * 「詳細クラスタ」で開いた結果を描画し、クラスタ一覧（ClusterOverview）の各カードが描画された回数を数える。
 * ClusterOverview だけが読む takeaway に getter を仕込み、読まれた回数を描画回数とみなす。
 */
async function renderDetailView() {
  const result = structuredClone(fixture) as unknown as Result;
  result.visualizationConfig = { defaultChart: "scatterDetail" } as Result["visualizationConfig"];
  const renders = new Map<string, number>();
  for (const cluster of result.clusters) {
    const takeaway = cluster.takeaway;
    Object.defineProperty(cluster, "takeaway", {
      enumerable: true,
      get() {
        renders.set(cluster.id, (renders.get(cluster.id) ?? 0) + 1);
        return takeaway;
      },
    });
  }
  render(
    <Provider>
      <ClientContainer result={result} />
    </Provider>,
  );
  await flush();
  return renders;
}

const total = (renders: Map<string, number>) => [...renders.values()].reduce((a, b) => a + b, 0);

it("詳細クラスタで表示設定ダイアログを開閉しても、クラスタ一覧のカードを描画し直さない", async () => {
  const renders = await renderDetailView();
  // 「詳細クラスタ」では最深階層（level 2）の 12 件を一覧に出す
  expect(screen.getAllByRole("heading", { level: 2 })).toHaveLength(12);
  expect([...renders.keys()].every((id) => id.startsWith("2_"))).toBe(true);
  renders.clear();

  // 表示設定ボタン（全画面表示ボタンの直前）を押してダイアログを開き、閉じる
  const settingButton = screen.getByRole("button", { name: "全画面表示" }).previousElementSibling as HTMLElement;
  fireEvent.click(settingButton);
  const dialog = await screen.findByRole("dialog");
  expect(dialog).toBeInTheDocument();
  await flush();
  fireEvent.keyDown(dialog, { key: "Escape" });
  await flush();

  expect(total(renders)).toBe(0);
});

it("散布図の点をクリックしたときは、選ばれたカードだけを描画し直す", async () => {
  const renders = await renderDetailView();
  renders.clear();

  fireEvent.click(screen.getByRole("button", { name: "クラスタ2_86を選択" }));
  await flush();

  expect([...renders.keys()]).toEqual(["2_86"]);
  expect(document.querySelector('[aria-current="true"]')?.textContent).toContain("AIの権利を通じた共存");
});

it("カードの見出しを押すと、そのクラスタを開いた階層表示へ移る", async () => {
  await renderDetailView();

  fireEvent.click(screen.getAllByRole("link")[0]);
  await flush();

  const firstLevel2 = [...fixture.clusters].filter((c) => c.level === 2).sort((a, b) => b.value - a.value)[0];
  expect(screen.getByTestId("treemap")).toHaveAttribute("data-level", firstLevel2.id);
});
