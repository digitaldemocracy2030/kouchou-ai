import { Provider } from "@/components/ui/provider";
import type { Argument, Cluster } from "@/type";
import { render } from "@testing-library/react";
import type { PlotMouseEvent } from "plotly.js";
import { ScatterChart } from "../ScatterChart";
import { TreemapChart, buildTreemapFigure } from "../TreemapChart";

// jsdom には structuredClone が無く、Chakra v3 の recipe 処理が必要とするため補う
globalThis.structuredClone ??= <T,>(value: T): T => (value === undefined ? value : JSON.parse(JSON.stringify(value)));

type ChartCoreProps = {
  data: unknown[];
  layout: unknown;
  config: unknown;
  onClick?: (event: PlotMouseEvent) => void;
  onTreemapClick?: (event: { nextLevel?: string }) => boolean;
};

// Plotly を実描画しないよう ChartCore をモックし、渡された props を記録する
const chartCoreProps: ChartCoreProps[] = [];
jest.mock("../ChartCore", () => ({
  ChartCore: (props: ChartCoreProps) => {
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
  cluster("0", 0, "", 4),
  cluster("1_0", 1, "0", 2),
  cluster("1_1", 1, "0", 2),
  cluster("2_0", 2, "1_0", 2),
  cluster("2_1", 2, "1_1", 2),
];
const args = [
  arg("a1", ["0", "1_0", "2_0"], 1),
  arg("a2", ["0", "1_1", "2_1"], 2),
  arg("a3", ["0", "1_0", "2_0"], 3),
  arg("a4", ["0", "1_1", "2_1"], 4),
];

const lastProps = () => chartCoreProps[chartCoreProps.length - 1];
const clickOn = (clusterId: string) =>
  ({ points: [{ customdata: { arg_id: "a1", cluster_id: clusterId } }] }) as unknown as PlotMouseEvent;

beforeEach(() => {
  chartCoreProps.length = 0;
});

describe("ScatterChart の描画データの memo", () => {
  function renderScatter(props: Partial<React.ComponentProps<typeof ScatterChart>> = {}) {
    const element = (override: Partial<React.ComponentProps<typeof ScatterChart>> = {}) => (
      <Provider>
        <ScatterChart
          clusterList={clusters}
          argumentList={args}
          targetLevel={1}
          showClusterLabels
          showConvexHull
          {...props}
          {...override}
        />
      </Provider>
    );
    const result = render(element());
    return { ...result, rerenderWith: (override = {}) => result.rerender(element(override)) };
  }

  it.each([
    ["フィルタなし", undefined],
    ["フィルタ中", ["a1", "a4"]],
  ])("%s: 同じ props で再描画しても、data・layout・config の参照が変わらない（Plotly.react が走らない）", (_, ids) => {
    const { rerenderWith } = renderScatter({ filteredArgumentIds: ids });
    const first = lastProps();
    rerenderWith();
    const second = lastProps();
    expect(second).not.toBe(first);
    expect(second.data).toBe(first.data);
    expect(second.layout).toBe(first.layout);
    expect(second.config).toBe(first.config);
  });

  it("フィルタが変わったときは data を作り直す", () => {
    const { rerenderWith } = renderScatter();
    const first = lastProps();
    rerenderWith({ filteredArgumentIds: ["a1"] });
    expect(lastProps().data).not.toBe(first.data);
  });

  it("ラベル表示を切り替えたときは layout を作り直す", () => {
    const { rerenderWith } = renderScatter();
    const first = lastProps();
    rerenderWith({ showClusterLabels: false });
    expect(lastProps().layout).not.toBe(first.layout);
    expect((lastProps().layout as { annotations: unknown[] }).annotations).toEqual([]);
  });

  it("描画し直さずに残ったクリックハンドラでも、最新の onSelectCluster を呼ぶ", () => {
    const oldSelect = jest.fn();
    const newSelect = jest.fn();
    const { rerenderWith } = renderScatter({ onSelectCluster: oldSelect });
    // react-plotly は描画データが変わらない限りハンドラを付け替えないので、初回のハンドラが残り続ける
    const firstOnClick = lastProps().onClick;
    rerenderWith({ onSelectCluster: newSelect });
    firstOnClick?.(clickOn("1_0"));
    expect(newSelect).toHaveBeenCalledWith("1_0");
    expect(oldSelect).not.toHaveBeenCalled();
  });
});

describe("TreemapChart の描画データの memo", () => {
  function renderTreemap(onTreeZoom: (level: string) => void, ids?: string[]) {
    const element = (zoom: (level: string) => void) => (
      <TreemapChart clusterList={clusters} argumentList={args} level="0" onTreeZoom={zoom} filteredArgumentIds={ids} />
    );
    const result = render(element(onTreeZoom));
    return { rerenderWith: (zoom: (level: string) => void) => result.rerender(element(zoom)) };
  }

  it("同じ入力で再描画しても、data・layout・config の参照が変わらない", () => {
    const zoom = jest.fn();
    const { rerenderWith } = renderTreemap(zoom, ["a1"]);
    const first = lastProps();
    rerenderWith(zoom);
    expect(lastProps().data).toBe(first.data);
    expect(lastProps().layout).toBe(first.layout);
    expect(lastProps().config).toBe(first.config);
  });

  it("描画し直さずに残ったクリックハンドラでも、最新の onTreeZoom を呼ぶ", () => {
    const oldZoom = jest.fn();
    const newZoom = jest.fn();
    const { rerenderWith } = renderTreemap(oldZoom);
    const firstOnTreemapClick = lastProps().onTreemapClick;
    rerenderWith(newZoom);
    expect(firstOnTreemapClick?.({ nextLevel: "1_0" })).toBe(false);
    expect(newZoom).toHaveBeenCalledWith("1_0");
    expect(oldZoom).not.toHaveBeenCalled();
  });
});

describe("buildTreemapFigure", () => {
  it("フィルタなしでは、クラスタの値は元の件数、意見の値は 1 になる", () => {
    // ルート表示では意見は見えないので、各小分類の代表 1 件だけが葉として渡る（treemapLeaves.test.ts）
    const { data } = buildTreemapFigure(clusters, args, "0", undefined);
    expect(data.ids).toEqual(["0", "1_0", "1_1", "2_0", "2_1", "a3", "a4"]);
    expect(data.parents).toEqual(["", "0", "0", "1_0", "1_1", "2_0", "2_1"]);
    expect(data.values).toEqual([4, 2, 2, 2, 2, 1, 1]);
    expect(data.level).toBe("0");
  });

  it("フィルタ中は、クラスタの値をフィルタ後の件数にし、合致しない意見を値 0・灰色・ホバーなしにする", () => {
    // 小分類 2_0 の表示では、その意見 a1・a3 と、見えない小分類 2_1 の代表 a4 が葉として渡る
    const { data } = buildTreemapFigure(clusters, args, "2_0", ["a1"]);
    expect(data.ids).toEqual(["0", "1_0", "1_1", "2_0", "2_1", "a1", "a3", "a4"]);
    expect(data.values).toEqual([1, 1, 0, 1, 0, 1, 0, 0]);
    expect((data.marker as { colors: string[] }).colors).toEqual(["", "", "", "", "", "", "#cccccc", "#cccccc"]);
    const customdata = data.customdata as string[];
    expect(customdata[1]).toContain("元の件数: 2<br>フィルター後: 1");
    expect(customdata[6]).toBe("");
    expect(data.texttemplate).toContain("(フィルター後)");
  });

  it("表示中の階層のラベルだけ広い幅で折り返す", () => {
    const long = { ...clusters[1], label: "あ".repeat(40) };
    const { data } = buildTreemapFigure([clusters[0], long, ...clusters.slice(2)], args, "1_0", undefined);
    const labels = data.labels as string[];
    expect(labels[1]).not.toContain("<br />");
    const narrow = buildTreemapFigure([clusters[0], long, ...clusters.slice(2)], args, "0", undefined).data
      .labels as string[];
    expect(narrow[1]).toContain("<br />");
  });
});
