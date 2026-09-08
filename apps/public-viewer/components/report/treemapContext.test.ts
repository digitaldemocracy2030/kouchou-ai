import { treemapContext } from "./treemapContext";

const clusters = [
  { id: "0", parent: "", label: "全体", takeaway: "", value: 3 },
  { id: "a", parent: "0", label: "交通", takeaway: "交通の説明", value: 2 },
  { id: "b", parent: "0", label: "教育", takeaway: "教育の説明", value: 1 },
  { id: "a1", parent: "a", label: "バス", takeaway: "バスの説明", value: 2 },
];
const opinions = [
  { arg_id: "x", argument: "バスを増やす", cluster_ids: ["0", "a", "a1"] },
  { arg_id: "y", argument: "運賃を下げる", cluster_ids: ["0", "a", "a1"] },
  { arg_id: "z", argument: "学校を増やす", cluster_ids: ["0", "b"] },
];

describe("階層図と説明の共通契約", () => {
  it("全体では直下だけを表示する", () => {
    const view = treemapContext(clusters, opinions, "0");
    expect(view.children.map((c) => c.id)).toEqual(["a", "b"]);
    expect(view.parent).toBeUndefined();
    expect(view.children[0].percentage).toBe("66.67%");
  });
  it("移動後は兄弟ではなく直下を表示し、親へ戻れる", () => {
    const view = treemapContext(clusters, opinions, "a");
    expect(view.current?.takeaway).toBe("交通の説明");
    expect(view.children.map((c) => c.id)).toEqual(["a1"]);
    expect(view.parent?.id).toBe("0");
    expect(view.children[0].percentage).toBe("66.67%");
  });
  it("末端グループと個別意見を区別する", () => {
    expect(treemapContext(clusters, opinions, "a1").children).toEqual([]);
    const view = treemapContext(clusters, opinions, "x");
    expect(view.current?.label).toBe("バスを増やす");
    expect(view.current?.count).toBe(1);
    expect(view.parent?.id).toBe("a1");
    expect(view.isOpinion).toBe(true);
  });
  it("フィルター後の件数と全体分母を使い、説明は保持する", () => {
    const view = treemapContext(clusters, opinions, "a", new Set(["x", "z"]));
    expect(view.current).toMatchObject({ count: 1, percentage: "50.00%", takeaway: "交通の説明" });
    expect(view.children[0].count).toBe(1);
    expect(treemapContext(clusters, opinions, "y", ["x"]).current?.count).toBe(0);
  });
  it("該当なしでも階層を保持しゼロ除算しない", () => {
    const view = treemapContext(clusters, opinions, "a", []);
    expect(view.current).toMatchObject({ id: "a", count: 0, percentage: "—" });
    expect(view.parent?.id).toBe("0");
  });
  it("未知の移動先は全体へ戻り、空レポートでも落ちない", () => {
    expect(treemapContext(clusters, opinions, "missing").current?.id).toBe("0");
    expect(treemapContext([], [], "0").current).toBeUndefined();
  });
});
