import type { Argument, Cluster } from "@/type";
import { buildTreemapFigure, selectTreemapLeaves } from "../TreemapChart";

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

// 2 階層: 0 → 1_0 → {2_0, 2_1}、0 → 1_1 → 2_2
const clusters = [
  cluster("0", 0, "", 6),
  cluster("1_0", 1, "0", 4),
  cluster("1_1", 1, "0", 2),
  cluster("2_0", 2, "1_0", 2),
  cluster("2_1", 2, "1_0", 2),
  cluster("2_2", 2, "1_1", 2),
];
const args = [
  arg("a1", ["0", "1_0", "2_0"]),
  arg("a2", ["0", "1_0", "2_0"]),
  arg("a3", ["0", "1_0", "2_1"]),
  arg("a4", ["0", "1_0", "2_1"]),
  arg("a5", ["0", "1_1", "2_2"]),
  arg("a6", ["0", "1_1", "2_2"]),
];

const leaf = (id: string, parent: string, filtered = false) => ({ id, parent, ...(filtered ? { filtered } : {}) });
const ids = (list: { id: string }[]) => list.map((node) => node.id);
const argIdsIn = (figureIds: unknown) => (figureIds as string[]).filter((id) => id.startsWith("a"));

describe("selectTreemapLeaves", () => {
  const leaves = [
    leaf("a1", "2_0"),
    leaf("a2", "2_0"),
    leaf("a3", "2_1"),
    leaf("a4", "2_1"),
    leaf("a5", "2_2"),
    leaf("a6", "2_2"),
  ];

  it("表示中の階層の直下にある意見はすべて残し、他のクラスタには代表を 1 件ずつ残す", () => {
    expect(ids(selectTreemapLeaves(clusters, leaves, "2_0"))).toEqual(["a1", "a2", "a4", "a6"]);
  });

  it("見えない階層のクラスタには、代表の意見を 1 件だけ残す（葉扱いにして色を変えないため）", () => {
    // ルート表示では意見はどれも見えない。各小分類に、並びで最後の意見を 1 件ずつ残す
    expect(ids(selectTreemapLeaves(clusters, leaves, "0"))).toEqual(["a2", "a4", "a6"]);
    expect(ids(selectTreemapLeaves(clusters, leaves, "1_0"))).toEqual(["a2", "a4", "a6"]);
  });

  it("代表には、フィルタで除外された（値 0 の）意見があればその最後を選ぶ", () => {
    const filteredLeaves = [
      leaf("a1", "2_0", true),
      leaf("a2", "2_0"),
      leaf("a3", "2_1"),
      leaf("a4", "2_1", true),
      leaf("a5", "2_2", true),
      leaf("a6", "2_2", true),
    ];
    expect(ids(selectTreemapLeaves(clusters, filteredLeaves, "0"))).toEqual(["a1", "a4", "a6"]);
  });

  it("1 階層のレポートでも、クラスタに入った表示では意見をすべて残す", () => {
    const flat = [cluster("0", 0, "", 3), cluster("1_0", 1, "0", 2), cluster("1_1", 1, "0", 1)];
    const flatLeaves = [leaf("b1", "1_0"), leaf("b2", "1_0"), leaf("b3", "1_1")];
    expect(ids(selectTreemapLeaves(flat, flatLeaves, "1_0"))).toEqual(["b1", "b2", "b3"]);
    expect(ids(selectTreemapLeaves(flat, flatLeaves, "0"))).toEqual(["b2", "b3"]);
  });

  it("level がクラスタでない想定外の値のときは絞らない", () => {
    expect(ids(selectTreemapLeaves(clusters, leaves, "a1"))).toEqual(ids(leaves));
  });
});

describe("buildTreemapFigure の葉の数", () => {
  it("ルート表示では、ノード数がクラスタ数＋見えないクラスタの代表数になる", () => {
    const { data } = buildTreemapFigure(clusters, args, "0", undefined);
    expect(data.ids).toHaveLength(clusters.length + 3);
    expect(argIdsIn(data.ids)).toEqual(["a2", "a4", "a6"]);
  });

  it("小分類の表示では、その小分類の意見をすべて渡す", () => {
    const { data } = buildTreemapFigure(clusters, args, "2_1", undefined);
    expect(argIdsIn(data.ids)).toEqual(["a2", "a3", "a4", "a6"]);
  });

  it("葉を絞っても、クラスタの値（フィルタ後の件数）と表示文言は変わらない", () => {
    const { data } = buildTreemapFigure(clusters, args, "0", ["a1", "a5"]);
    const valueById = Object.fromEntries((data.ids as string[]).map((id, i) => [id, (data.values as number[])[i]]));
    expect(valueById).toMatchObject({ "0": 2, "1_0": 1, "1_1": 1, "2_0": 1, "2_1": 0, "2_2": 1 });
    const customdata = data.customdata as string[];
    expect(customdata[(data.ids as string[]).indexOf("1_0")]).toContain("元の件数: 4<br>フィルター後: 1");
  });
});
