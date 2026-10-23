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

async function renderViewer(overrides: Partial<Result> = {}) {
  const result = { ...(structuredClone(fixture) as unknown as Result), ...overrides };
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

describe("濃い意見の抽出結果が 0 件のとき", () => {
  it("一つ上の階層を濃い意見として表示せず、全体表示へ戻す", async () => {
    await renderViewer({
      visualizationConfig: {
        defaultChart: "scatterDensity",
        // どのクラスタも条件を満たさない最小件数
        params: { scatterDensity: { maxDensity: 1, minValue: 1_000_000 } },
      },
    } as Partial<Result>);

    expect(screen.getByRole("radio", { name: "全体" })).toBeChecked();
    expect(screen.getByRole("radio", { name: "濃い意見" })).not.toBeChecked();
    expect(screen.getByTestId("scatter")).toHaveAttribute("data-level", "1");
    await flush();
  });

  it("管理者が「全体」を外していれば、有効な表示の中から選び直す", async () => {
    await renderViewer({
      visualizationConfig: {
        enabledCharts: ["scatterDensity", "treemap"],
        defaultChart: "scatterDensity",
        params: { scatterDensity: { maxDensity: 1, minValue: 1_000_000 } },
      },
    } as Partial<Result>);

    expect(screen.queryByRole("radio", { name: "全体" })).not.toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "階層" })).toBeChecked();
    expect(screen.getByRole("radio", { name: "濃い意見" })).not.toBeChecked();
    expect(screen.getByTestId("treemap")).toBeInTheDocument();
    expect(screen.queryByTestId("scatter")).not.toBeInTheDocument();
    await flush();
  });

  it("「全体」が無いときは、表示順で先頭の選べる表示へ戻す", async () => {
    await renderViewer({
      visualizationConfig: {
        enabledCharts: ["scatterDensity", "treemap", "hierarchyList"],
        chartOrder: ["scatterDensity", "hierarchyList", "treemap"],
        defaultChart: "scatterDensity",
        params: { scatterDensity: { maxDensity: 1, minValue: 1_000_000 } },
      },
    } as Partial<Result>);

    expect(screen.getByRole("radio", { name: "リスト" })).toBeChecked();
    expect(screen.getByTestId("hierarchy-list")).toBeInTheDocument();
    await flush();
  });

  it("他に選べる表示が無ければ、外された「全体」へは切り替えず濃い意見のまま（最深階層）にする", async () => {
    await renderViewer({
      visualizationConfig: {
        enabledCharts: ["scatterDensity"],
        defaultChart: "scatterDensity",
        params: { scatterDensity: { maxDensity: 1, minValue: 1_000_000 } },
      },
    } as Partial<Result>);
    const deepest = Math.max(...fixture.clusters.map((c) => c.level));

    expect(screen.queryByRole("radio", { name: "全体" })).not.toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "濃い意見" })).toBeChecked();
    expect(screen.getByTestId("scatter")).toHaveAttribute("data-level", String(deepest));
    // 一つ上の階層のクラスタを濃い意見として一覧に出さない
    for (const c of fixture.clusters.filter((c) => c.level === deepest - 1)) {
      expect(screen.queryByText(c.label)).not.toBeInTheDocument();
    }
    await flush();
  });
});

describe("フィルタボタン", () => {
  it("属性のあるレポートではフィルタボタンからテキスト検索に到達できる", async () => {
    await renderViewer();
    fireEvent.click(screen.getByRole("button", { name: "フィルタ" }));
    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByText("テキスト検索")).toBeInTheDocument();
    await flush();
  });

  it("属性の無いレポート（attributes=null）でも、フィルタボタンからテキスト検索を使える", async () => {
    // 属性列を選ばずに作ったレポートでは analysis-core が attributes: null を出力する
    const args = (structuredClone(fixture) as unknown as Result).arguments.map((a) => ({
      ...a,
      attributes: null,
    })) as unknown as Result["arguments"];
    await renderViewer({ arguments: args });

    fireEvent.click(screen.getByRole("button", { name: "フィルタ" }));
    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByText("テキスト検索")).toBeInTheDocument();
    // 属性 0 件の案内は閲覧者向けの文言にする（作成者向けの「CSVファイルをアップロードする際に…」は出さない）
    expect(within(dialog).getByText("このレポートには、絞り込みに使える属性情報がありません。")).toBeInTheDocument();
    expect(within(dialog).queryByText(/CSVファイルをアップロード/)).not.toBeInTheDocument();

    fireEvent.change(within(dialog).getByRole("textbox"), { target: { value: "AI" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "設定を適用" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());

    // 検索中であることがバッジ（有効なフィルタ数）でわかる
    expect(within(screen.getByRole("button", { name: "フィルタ" })).getByText("1")).toBeInTheDocument();
    await flush();
  });
});
