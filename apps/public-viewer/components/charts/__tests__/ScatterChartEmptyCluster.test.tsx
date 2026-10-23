import { Provider } from "@/components/ui/provider";
import type { Argument, Cluster } from "@/type";
import { render } from "@testing-library/react";
import { ScatterChart } from "../ScatterChart";

// jsdom には structuredClone が無く、Chakra v3 の recipe 処理が必要とするため補う
globalThis.structuredClone ??= <T,>(value: T): T => (value === undefined ? value : JSON.parse(JSON.stringify(value)));

// Plotly を実描画せず、ChartCore に渡る layout だけを取り出す
const chartCoreProps: Array<{ layout?: { annotations?: Array<{ x: number; y: number; text: string }> } }> = [];
jest.mock("../ChartCore", () => ({
  ChartCore: (props: unknown) => {
    chartCoreProps.push(props as (typeof chartCoreProps)[number]);
    return null;
  },
}));

// lucide-react は ESM のみ配布のため空コンポーネントに差し替える
jest.mock("lucide-react", () => new Proxy({}, { get: (_, name) => (name === "__esModule" ? true : () => null) }));

const cluster = (id: string, label: string, value: number): Cluster => ({
  id,
  level: 1,
  label,
  takeaway: "",
  value,
  parent: "0",
  density_rank_percentile: 0.5,
});

const arg = (argId: string, clusterId: string, x: number, y: number): Argument => ({
  arg_id: argId,
  argument: `arg-${argId}`,
  comment_id: 0,
  x,
  y,
  p: 0,
  cluster_ids: ["0", clusterId],
});

// 指定カテゴリ分類で全意見がカテゴリに収まり、受け皿の「その他」が 0 件で残ったレポート
const clusters: Cluster[] = [
  { ...cluster("0", "全体", 3), level: 0, parent: "" },
  cluster("g1", "交通", 2),
  cluster("g2", "医療", 1),
  cluster("other", "その他", 0),
];
const args = [arg("A1", "g1", 8, -1), arg("A2", "g1", 9, -1.5), arg("A3", "g2", 10, -2)];

function lastAnnotations() {
  const annotations = chartCoreProps.at(-1)?.layout?.annotations ?? [];
  return annotations.map((a) => ({ text: a.text, x: a.x, y: a.y }));
}

describe("ScatterChart: 意見が 0 件のクラスタ", () => {
  beforeEach(() => {
    chartCoreProps.length = 0;
  });

  it.each([
    ["フィルタなし", undefined],
    ["フィルタ中", ["A1"]],
  ])("%s: 0 件のクラスタのラベルを原点 (0,0) に置かない", (_, filteredArgumentIds) => {
    render(
      <Provider>
        <ScatterChart
          clusterList={clusters}
          argumentList={args}
          targetLevel={1}
          showClusterLabels
          filteredArgumentIds={filteredArgumentIds}
        />
      </Provider>,
    );

    const annotations = lastAnnotations();
    expect(annotations.map((a) => a.text)).toEqual(["交通", "医療"]);
    expect(annotations).not.toContainEqual(expect.objectContaining({ x: 0, y: 0 }));
  });
});
