import "@testing-library/jest-dom";
import { Provider } from "@/components/ui/provider";
import { LanguageProvider } from "@/lib/i18n/LanguageContext";
import type { Result } from "@/type";
import { act, fireEvent, render, screen } from "@testing-library/react";
import fixture from "../dev/viewer-fixture.json";
import { Chart } from "./Chart";

// jsdom には structuredClone が無く、Chakra v3 の recipe 処理が必要とするため補う
globalThis.structuredClone ??= <T,>(value: T): T => (value === undefined ? value : JSON.parse(JSON.stringify(value)));

// lucide-react は ESM のみ配布で Jest が変換しないため、全アイコンを空コンポーネントにする
jest.mock("lucide-react", () => new Proxy({}, { get: (_, name) => (name === "__esModule" ? true : () => null) }));

// Plotly を読み込まない
jest.mock("@/components/charts/ScatterChart", () => ({
  ScatterChart: (props: { targetLevel: number }) => <div data-testid="scatter" data-level={props.targetLevel} />,
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
  // Chakra の Dialog（zag.js）は ResizeObserver を要求する（jsdom には無い）
  class ResizeObserverStub {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  Object.defineProperty(window, "ResizeObserver", { writable: true, value: ResizeObserverStub });
});

/** zag.js の Dialog が requestAnimationFrame 後に行う状態更新を act 内で流す */
async function flush() {
  await act(async () => {
    await new Promise((resolve) => setTimeout(resolve, 50));
  });
}

/** 密度フィルタで最深 level のクラスタが全て落ちた状態の結果（level 1 だけが残る） */
function resultWithoutDeepestLevel(): { full: Result; filtered: Result } {
  const full = structuredClone(fixture) as unknown as Result;
  const filtered = structuredClone(full);
  filtered.clusters = filtered.clusters.filter((c) => c.level <= 1);
  return { full, filtered };
}

async function renderFullscreen(props: Partial<React.ComponentProps<typeof Chart>>) {
  const utils = render(
    <Provider>
      <Chart
        result={props.result as Result}
        selectedChart="scatterAll"
        isFullscreen
        onExitFullscreen={() => {}}
        onChangeChart={() => {}}
        showClusterLabels
        onToggleClusterLabels={() => {}}
        showConvexHull
        treemapLevel="0"
        onTreeZoom={() => {}}
        {...props}
      />
    </Provider>,
  );
  await flush();
  return utils;
}

describe("全画面の粒度切替が選べるモードの判定", () => {
  it("密度フィルタで最深 level が全て落ちても、modeResult（フィルタ前）から詳細クラスタを選べる", async () => {
    const { full, filtered } = resultWithoutDeepestLevel();
    await renderFullscreen({ result: filtered, modeResult: full });
    expect(screen.getByRole("button", { name: "詳細クラスタ" })).toBeEnabled();
  });

  it("modeResult が無ければ描画用の result で判定する（最深 level が無いので詳細クラスタは無効）", async () => {
    const { filtered } = resultWithoutDeepestLevel();
    await renderFullscreen({ result: filtered });
    expect(screen.getByRole("button", { name: "詳細クラスタ" })).toBeDisabled();
  });
});

describe("全画面ツールバーの言語切替", () => {
  const result = {
    arguments: [],
    clusters: [{ level: 1, id: "1", label: "交通", takeaway: "", value: 1, parent: "0", density_rank_percentile: 0 }],
    comments: {},
    propertyMap: {},
    translations: {},
    overview: "",
    config: {},
    comment_num: 0,
  } as unknown as Result;

  beforeEach(() => {
    window.localStorage.clear();
    window.history.replaceState(null, "", "/report-1");
  });

  it("全画面表示のツールバーに言語切替があり、全画面のまま切り替えられる", () => {
    render(
      <Provider>
        <LanguageProvider>
          <Chart
            result={result}
            selectedChart="scatterAll"
            isFullscreen
            onExitFullscreen={() => {}}
            showClusterLabels
            onToggleClusterLabels={() => {}}
            showConvexHull
            treemapLevel="0"
            onTreeZoom={() => {}}
          />
        </LanguageProvider>
      </Provider>,
    );
    const toolbar = document.getElementById("fullScreenButtons");
    expect(toolbar).not.toBeNull();
    expect(toolbar).toContainElement(screen.getByTestId("language-toggle"));
    expect(toolbar).toContainElement(screen.getByRole("button", { name: "全画面終了" }));

    fireEvent.click(screen.getByRole("button", { name: "한국어" }));

    expect(toolbar).toContainElement(screen.getByRole("button", { name: "전체 화면 종료" }));
    expect(screen.getByTestId("scatter")).toBeInTheDocument();
    expect(window.location.search).toBe("?lang=ko");
  });
});
