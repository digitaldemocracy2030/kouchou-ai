import type { ClusterOutline, Point } from "../charts/scatterOutlines";
import {
  clipScatterOutlines,
  containsPoint,
  inspectScatterOverlaps,
  makeScatterOutlineClipper,
} from "./clipScatterOutlines";

function rectangle(id: string, left: number, bottom: number, right: number, top: number): ClusterOutline {
  const hull: Point[] = [
    [left, bottom],
    [right, bottom],
    [right, top],
    [left, top],
  ];
  return { id, hull, points: hull };
}

it("削る側の点が重なりに無ければ、片側だけ切り取る", () => {
  const a = rectangle("a", 0, 0, 4, 4);
  const b = rectangle("b", 2, 1, 5, 3);
  const { result, stats } = clipScatterOutlines([a, b]);
  const trimmed = result.get(a.id);
  expect(trimmed).toBeDefined();
  expect(containsPoint([3, 2], trimmed ?? [])).toBe(false);
  expect(a.points.every((p) => containsPoint(p, trimmed ?? []))).toBe(true);
  expect(result.has(b.id)).toBe(false);
  expect(stats).toMatchObject({ oneSided: 1, remaining: 0, rejected: 0 });
});

it("包含されたクラスタの周りには穴を作る", () => {
  const outer = rectangle("outer", 0, 0, 4, 4);
  const inner = rectangle("inner", 1, 1, 2, 2);
  const { result, stats } = clipScatterOutlines([outer, inner]);
  const trimmed = result.get(outer.id);
  expect(trimmed).toHaveLength(2);
  expect(containsPoint([1.5, 1.5], trimmed ?? [])).toBe(false);
  expect(containsPoint([0.5, 0.5], trimmed ?? [])).toBe(true);
  expect(stats.remaining).toBe(0);
});

it("両側の点が重なりにあれば、重なりの内側だけ直線で分ける", () => {
  const a = rectangle("a", 0, 0, 4, 4);
  const b = rectangle("b", 2, 2, 6, 6);
  const { result, stats } = clipScatterOutlines([a, b]);
  expect(stats).toMatchObject({ straight: 1, remaining: 0, rejected: 0 });
  for (const outline of [a, b]) {
    const trimmed = result.get(outline.id) ?? [];
    expect(outline.points.every((p) => containsPoint(p, trimmed))).toBe(true);
  }
  for (const p of [
    [2.3, 3.2],
    [3.9, 3.6],
    [3.2, 2.7],
  ] as Point[]) {
    expect(Number(containsPoint(p, result.get("a") ?? [])) + Number(containsPoint(p, result.get("b") ?? []))).toBe(1);
  }
});

it("点を分けられない場合と辺が接するだけの場合は切り取らない", () => {
  const a = rectangle("a", 0, 0, 4, 4);
  const b = rectangle("b", 0, 0, 4, 4);
  const c = rectangle("c", 4, 0, 8, 4);
  const { result, stats } = clipScatterOutlines([a, b, c]);
  expect(result.size).toBe(0);
  expect(stats).toMatchObject({ overlaps: 1, remaining: 1, rejected: 0 });
});

it("3 クラスタの候補は入力の順序を変えても同じ順で処理し、点を保持する", () => {
  const a = rectangle("a", 0, 0, 5, 5);
  const b = rectangle("b", 2, 1, 6, 3);
  const c = rectangle("c", 3, 2, 7, 4);
  const outlines = [a, b, c];
  const clipped = clipScatterOutlines(outlines);
  expect(clipped).toEqual(clipScatterOutlines([c, a, b]));
  expect(clipped.stats.oneSided + clipped.stats.straight).toBeGreaterThan(0);
  for (const outline of outlines) {
    const rings = clipped.result.get(outline.id) ?? [outline.hull];
    expect(outline.points.every((p) => containsPoint(p, rings))).toBe(true);
  }
});

it("拡大表示の判定は元の重なりを保持し、処理後に残る組を区別する", () => {
  const a = rectangle("a", 0, 0, 4, 4);
  const b = rectangle("b", 0, 0, 4, 4);
  const c = rectangle("c", 8, 0, 12, 4);
  const d = rectangle("d", 10, 2, 14, 6);
  const { cases } = inspectScatterOverlaps([a, b, c, d]);
  expect(cases.map(({ ids, resolved }) => [ids, resolved])).toEqual([
    [["a", "b"], false],
    [["c", "d"], true],
  ]);
  expect(containsPoint([11, 3], cases[1].originalRings)).toBe(true);
  expect(containsPoint([2, 2], cases[0].remainingRings)).toBe(true);
  expect(cases[1].remainingRings).toHaveLength(0);
});

it("局所分割に渡すのは、直線で分けられなかった組の重なりにある点だけ", () => {
  const a = rectangle("a", 0, 0, 6, 6);
  const b = rectangle("b", 2, 2, 8, 8);
  a.points = [...a.points, [3, 3]];
  b.points = [...b.points, [5, 5]];
  const c = rectangle("c", 10, 0, 14, 4);
  const d = rectangle("d", 12, 2, 16, 6);
  const partition = jest.fn(() => undefined);

  const { result, stats } = makeScatterOutlineClipper(partition)([a, b, c, d]);

  expect(partition).toHaveBeenCalledTimes(1);
  expect(partition).toHaveBeenCalledWith(
    [
      [6 / 16, 6 / 16],
      [3 / 16, 3 / 16],
    ],
    [
      [2 / 16, 2 / 16],
      [5 / 16, 5 / 16],
    ],
    { minX: 2 / 16, minY: 2 / 16, maxX: 6 / 16, maxY: 6 / 16 },
  );
  expect(result.has(a.id)).toBe(false);
  expect(result.has(b.id)).toBe(false);
  expect(stats).toMatchObject({ straight: 1, remaining: 1, voronoi: 0, rejected: 1 });
});
