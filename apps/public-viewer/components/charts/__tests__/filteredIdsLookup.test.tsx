import { Provider } from "@/components/ui/provider";
import type { Argument, Cluster } from "@/type";
import { fireEvent, render, screen } from "@testing-library/react";
import { HierarchyListChart } from "../HierarchyListChart";
import { ScatterChart } from "../ScatterChart";
import { TreemapChart } from "../TreemapChart";

// jsdom には structuredClone が無く、Chakra v3 の recipe 処理が必要とするため補う
globalThis.structuredClone ??= <T,>(value: T): T => (value === undefined ? value : JSON.parse(JSON.stringify(value)));

// Plotly を実描画しないよう ChartCore をモックする（描画に渡すデータの検証が目的のため）
const chartCoreProps: { data: unknown[]; layout: { annotations?: unknown[] } }[] = [];
jest.mock("../ChartCore", () => ({
  ChartCore: (props: { data: unknown[]; layout: { annotations?: unknown[] } }) => {
    chartCoreProps.push(props);
    return null;
  },
}));

// lucide-react は ESM のみ配布のため空コンポーネントに差し替える
jest.mock("lucide-react", () => new Proxy({}, { get: (_, name) => (name === "__esModule" ? true : () => null) }));

const cluster = (id: string, level: number, parent: string, value: number): Cluster => ({
  id,
  level,
  label: `cluster-${id}`,
  takeaway: `takeaway-${id}`,
  value,
  parent,
  density_rank_percentile: 0.1,
});

const arg = (argId: string, clusterIds: string[], x: number): Argument => ({
  arg_id: argId,
  argument: `arg-${argId}`,
  comment_id: 0,
  x,
  y: x,
  p: 0,
  cluster_ids: clusterIds,
});

const clusters = [
  cluster("0", 0, "", 5),
  cluster("1_0", 1, "0", 3),
  cluster("1_1", 1, "0", 2),
  cluster("2_0", 2, "1_0", 3),
  cluster("2_1", 2, "1_1", 2),
];
const args = [
  arg("a1", ["0", "1_0", "2_0"], 1),
  arg("a2", ["0", "1_1", "2_1"], 2),
  arg("a3", ["0", "1_0", "2_0"], 3),
  arg("a4", ["0", "1_1", "2_1"], 4),
  arg("a5", ["0", "1_0", "2_0"], 5),
];

/**
 * includes が呼ばれた回数を数えるフィルタ ID 配列を作る。
 * 描画側が配列の線形探索（N×|F|）に戻っていないことを、時間ではなく呼び出し回数で検証するため。
 */
function countingIds(ids: string[]) {
  const counter = { calls: 0 };
  const array = [...ids];
  Object.defineProperty(array, "includes", {
    value: (...params: Parameters<string[]["includes"]>) => {
      counter.calls++;
      return Array.prototype.includes.apply(array, params);
    },
  });
  return { array, counter };
}

type Trace = { customdata: { arg_id: string; cluster_id: string }[]; marker: { size: number } };
const argIdsOf = (trace: Trace) => trace.customdata.map((d) => d.arg_id);

beforeEach(() => {
  chartCoreProps.length = 0;
});

describe("ScatterChart のフィルタ判定", () => {
  it("フィルタ ID の配列を線形探索（includes）しない", () => {
    const { array, counter } = countingIds(["a1", "a4"]);
    render(
      <Provider>
        <ScatterChart
          clusterList={clusters}
          argumentList={args}
          targetLevel={1}
          showClusterLabels
          filteredArgumentIds={array}
        />
      </Provider>,
    );
    expect(counter.calls).toBe(0);
  });

  it("フィルタ中は、各クラスタを合致しない点（背面・灰色）と合致する点（前面）のトレースに分ける", () => {
    render(
      <Provider>
        <ScatterChart clusterList={clusters} argumentList={args} targetLevel={1} filteredArgumentIds={["a1", "a4"]} />
      </Provider>,
    );
    const data = chartCoreProps[chartCoreProps.length - 1].data as Trace[];
    expect(data.map(argIdsOf)).toEqual([
      ["a3", "a5"], // 1_0 の合致しない点
      ["a1"], // 1_0 の合致する点
      ["a2"], // 1_1 の合致しない点
      ["a4"], // 1_1 の合致する点
    ]);
    expect(data.map((t) => t.marker.size)).toEqual([7, 10, 7, 10]);
  });

  it("フィルタで全点が除外されたクラスタは、全点を灰色のトレースとして残す", () => {
    render(
      <Provider>
        <ScatterChart clusterList={clusters} argumentList={args} targetLevel={1} filteredArgumentIds={["a2"]} />
      </Provider>,
    );
    const data = chartCoreProps[chartCoreProps.length - 1].data as Trace[];
    expect(data.map(argIdsOf)).toEqual([["a1", "a3", "a5"], ["a4"], ["a2"]]);
  });
});

describe("TreemapChart のフィルタ判定", () => {
  it("フィルタ ID の配列を線形探索（includes）しない", () => {
    const { array, counter } = countingIds(["a1", "a4"]);
    render(
      <TreemapChart
        clusterList={clusters}
        argumentList={args}
        level="0"
        onTreeZoom={() => {}}
        filteredArgumentIds={array}
      />,
    );
    expect(counter.calls).toBe(0);
  });

  it("フィルタ後の件数をクラスタの値に、合致しない意見を 0 にする", () => {
    render(
      <TreemapChart
        clusterList={clusters}
        argumentList={args}
        level="0"
        onTreeZoom={() => {}}
        filteredArgumentIds={["a1", "a4"]}
      />,
    );
    const [trace] = chartCoreProps[chartCoreProps.length - 1].data as { ids: string[]; values: number[] }[];
    const valueById = Object.fromEntries(trace.ids.map((id, i) => [id, trace.values[i]]));
    expect(valueById).toEqual({ "0": 2, "1_0": 1, "1_1": 1, "2_0": 1, "2_1": 1, a1: 1, a2: 0, a3: 0, a4: 1, a5: 0 });
  });
});

describe("HierarchyListChart のフィルタ判定", () => {
  function expandAll() {
    for (let i = 0; i < 4; i++) {
      for (const button of screen.queryAllByRole("button", { name: "展開する" })) fireEvent.click(button);
      for (const button of screen.queryAllByText(/^(子要素を表示|個別データを表示)/)) fireEvent.click(button);
    }
  }

  it("個別データの表示でフィルタ ID の配列を線形探索（includes）しない", () => {
    const { array, counter } = countingIds(["a1", "a4"]);
    render(
      <Provider>
        <HierarchyListChart clusterList={clusters} argumentList={args} filteredArgumentIds={array} />
      </Provider>,
    );
    expandAll();
    expect(screen.getByText("arg-a3")).toBeInTheDocument();
    expect(counter.calls).toBe(0);
  });

  it("最深階層のクラスタに、そのクラスタの意見を元の順序で表示する", () => {
    render(
      <Provider>
        <HierarchyListChart clusterList={clusters} argumentList={args} />
      </Provider>,
    );
    expandAll();
    const texts = screen.getAllByText(/^arg-a/).map((el) => el.textContent);
    expect(texts).toEqual(["arg-a1", "arg-a3", "arg-a5", "arg-a2", "arg-a4"]);
  });
});
