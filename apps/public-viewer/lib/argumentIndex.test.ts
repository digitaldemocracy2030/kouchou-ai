import type { Argument } from "@/type";
import { groupArgumentsByCluster, splitArgumentsByFilter, toIdSet } from "./argumentIndex";

const arg = (argId: string, clusterIds: string[]): Argument => ({
  arg_id: argId,
  argument: `arg-${argId}`,
  comment_id: 0,
  x: 0,
  y: 0,
  p: 0,
  cluster_ids: clusterIds,
});

const args = [
  arg("a1", ["0", "1_0", "2_0"]),
  arg("a2", ["0", "1_1", "2_1"]),
  arg("a3", ["0", "1_0", "2_2"]),
  arg("a4", ["0", "1_0", "2_0"]),
];

const ids = (list: Argument[]) => list.map((a) => a.arg_id);

describe("toIdSet", () => {
  it("フィルタなし（undefined）は undefined のまま返す", () => {
    expect(toIdSet(undefined)).toBeUndefined();
  });

  it("0 件一致のフィルタは空の Set として残し、フィルタなしと区別する", () => {
    const set = toIdSet([]);
    expect(set).toBeDefined();
    expect(set?.size).toBe(0);
  });

  it("配列の要素をすべて含む", () => {
    const set = toIdSet(["a1", "a3"]);
    expect(set?.has("a1")).toBe(true);
    expect(set?.has("a3")).toBe(true);
    expect(set?.has("a2")).toBe(false);
  });
});

describe("groupArgumentsByCluster", () => {
  it("各クラスタの意見一覧が、argumentList.filter(cluster_ids.includes) と同じ内容・同じ順序になる", () => {
    const index = groupArgumentsByCluster(args);
    for (const clusterId of ["0", "1_0", "1_1", "2_0", "2_1", "2_2"]) {
      expect(ids(index.get(clusterId) ?? [])).toEqual(ids(args.filter((a) => a.cluster_ids.includes(clusterId))));
    }
    expect(ids(index.get("1_0") ?? [])).toEqual(["a1", "a3", "a4"]);
  });

  it("意見の無いクラスタは索引に入らない", () => {
    expect(groupArgumentsByCluster(args).get("2_9")).toBeUndefined();
  });

  it("cluster_ids に同じ ID が重複していても、同じ意見は 1 回だけ入る", () => {
    const index = groupArgumentsByCluster([arg("b1", ["0", "1_0", "1_0"]), arg("b2", ["1_0"])]);
    expect(ids(index.get("1_0") ?? [])).toEqual(["b1", "b2"]);
  });
});

describe("splitArgumentsByFilter", () => {
  it("フィルタなしのときは、すべてを matching にし notMatching は空にする", () => {
    const { matching, notMatching } = splitArgumentsByFilter(args, undefined);
    expect(ids(matching)).toEqual(["a1", "a2", "a3", "a4"]);
    expect(notMatching).toEqual([]);
  });

  it("フィルタに合致する意見と合致しない意見を、入力の順序を保って分ける", () => {
    const { matching, notMatching } = splitArgumentsByFilter(args, new Set(["a4", "a2"]));
    expect(ids(matching)).toEqual(["a2", "a4"]);
    expect(ids(notMatching)).toEqual(["a1", "a3"]);
  });

  it("0 件一致のフィルタでは、すべてが notMatching になる", () => {
    const { matching, notMatching } = splitArgumentsByFilter(args, new Set());
    expect(matching).toEqual([]);
    expect(ids(notMatching)).toEqual(["a1", "a2", "a3", "a4"]);
  });

  it("入力の配列を変更しない", () => {
    const input = [...args];
    const { matching } = splitArgumentsByFilter(input, undefined);
    matching.pop();
    expect(input).toHaveLength(4);
  });
});
