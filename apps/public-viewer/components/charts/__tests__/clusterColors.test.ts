import type { Argument, Cluster } from "@/type";
import { buildTreemapFigure } from "../TreemapChart";
import { CLUSTER_COLORS, buildClusterColorMap, clusterColor } from "../clusterColors";

jest.mock("../ChartCore", () => ({ ChartCore: () => null }));

const cluster = (id: string, level: number, parent: string, value: number): Cluster => ({
  id,
  level,
  label: `cluster-${id}`,
  takeaway: "",
  value,
  parent,
  density_rank_percentile: 0.1,
});

const arg = (argId: string, clusterIds: string[]): Argument => ({
  arg_id: argId,
  argument: `arg-${argId}`,
  comment_id: 0,
  x: 0,
  y: 0,
  p: 0,
  cluster_ids: clusterIds,
});

// 第一階層は並び順と大きさの順が逆（1_0 が小さく 1_1 が大きい）
const clusters = [
  cluster("0", 0, "", 4),
  cluster("1_0", 1, "0", 1),
  cluster("1_1", 1, "0", 3),
  cluster("2_0", 2, "1_0", 1),
  cluster("2_1", 2, "1_1", 3),
];
const args = [
  arg("a1", ["0", "1_0", "2_0"]),
  arg("a2", ["0", "1_1", "2_1"]),
  arg("a3", ["0", "1_1", "2_1"]),
  arg("a4", ["0", "1_1", "2_1"]),
];

function colorsById(figure: ReturnType<typeof buildTreemapFigure>) {
  const ids = figure.data.ids as string[];
  const colors = (figure.data.marker as { colors: string[] }).colors;
  return Object.fromEntries(ids.map((id, i) => [id, colors[i]]));
}

describe("clusterColors", () => {
  it("並び順で色を決め、パレットの数を超えたら先頭から繰り返す", () => {
    expect(clusterColor(0)).toBe(CLUSTER_COLORS[0]);
    expect(clusterColor(CLUSTER_COLORS.length + 1)).toBe(CLUSTER_COLORS[1]);
    expect(buildClusterColorMap([clusters[1], clusters[2]])).toEqual({
      "1_0": CLUSTER_COLORS[0],
      "1_1": CLUSTER_COLORS[1],
    });
  });
});

describe("buildTreemapFigure の配色（#337）", () => {
  it("第一階層の意見グループに、全体図と同じ並び順の色を明示する", () => {
    const byId = colorsById(buildTreemapFigure(clusters, args, "0", undefined));
    // 全体図（散布図）は level 1 のクラスタを clusterList の並び順で塗る
    const scatterAll = buildClusterColorMap(clusters.filter((c) => c.level === 1));
    expect(byId["1_0"]).toBe(scatterAll["1_0"]);
    expect(byId["1_1"]).toBe(scatterAll["1_1"]);
    // ルート・第二階層より下は空にして、Plotly に親の色を引き継がせる
    expect(byId["0"]).toBe("");
    expect(byId["2_0"]).toBe("");
    expect(byId.a1).toBe("");
  });

  it("フィルタで外れた意見は灰色のまま", () => {
    // 2_1 の表示では、その意見 a2〜a4 が葉として渡る
    const byId = colorsById(buildTreemapFigure(clusters, args, "2_1", ["a2"]));
    expect(byId.a2).toBe("");
    expect(byId.a3).toBe("#cccccc");
    expect(byId.a4).toBe("#cccccc");
    expect(byId["1_1"]).toBe(CLUSTER_COLORS[1]);
  });
});
