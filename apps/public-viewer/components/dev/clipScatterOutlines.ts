import PolyBool, { type Polygon } from "polybooljs";
import type { ClusterOutline, OutlineClipper, Point } from "../charts/scatterOutlines";

type Bounds = { minX: number; minY: number; maxX: number; maxY: number };
const EPS = 1e-9;
const MIN_AREA = 1e-12;

function bounds(points: Point[]): Bounds {
  const box = {
    minX: Number.POSITIVE_INFINITY,
    minY: Number.POSITIVE_INFINITY,
    maxX: Number.NEGATIVE_INFINITY,
    maxY: Number.NEGATIVE_INFINITY,
  };
  for (const [x, y] of points) {
    box.minX = Math.min(box.minX, x);
    box.minY = Math.min(box.minY, y);
    box.maxX = Math.max(box.maxX, x);
    box.maxY = Math.max(box.maxY, y);
  }
  return box;
}

function signedArea(ring: Point[]) {
  let twiceArea = 0;
  for (let i = 0; i < ring.length; i++) {
    const [x, y] = ring[i];
    const next = ring[(i + 1) % ring.length];
    twiceArea += x * next[1] - y * next[0];
  }
  return twiceArea / 2;
}

function hasArea(polygon: Polygon) {
  return polygon.regions.some((ring) => Math.abs(signedArea(ring)) > MIN_AREA);
}

function nearBox([x, y]: Point, box: Bounds) {
  return x >= box.minX - EPS && x <= box.maxX + EPS && y >= box.minY - EPS && y <= box.maxY + EPS;
}

export function containsPoint([x, y]: Point, rings: Point[][]): boolean {
  let inside = false;
  for (const ring of rings) {
    for (let i = 0, j = ring.length - 1; i < ring.length; j = i, i++) {
      const [ax, ay] = ring[j];
      const [bx, by] = ring[i];
      const dx = bx - ax;
      const dy = by - ay;
      if (
        x >= Math.min(ax, bx) - EPS &&
        x <= Math.max(ax, bx) + EPS &&
        y >= Math.min(ay, by) - EPS &&
        y <= Math.max(ay, by) + EPS
      ) {
        const cross = dx * (y - ay) - dy * (x - ax);
        if (cross * cross <= EPS * EPS * (dx * dx + dy * dy)) return true;
      }
      if (ay > y !== by > y && x < ax + ((bx - ax) * (y - ay)) / (by - ay)) inside = !inside;
    }
  }
  return inside;
}

function supportHull(points: Point[]) {
  const sorted = [...points].sort(([ax, ay], [bx, by]) => ax - bx || ay - by);
  const unique = sorted.filter(([x, y], i) => i === 0 || x !== sorted[i - 1][0] || y !== sorted[i - 1][1]);
  if (unique.length <= 2) return unique;
  const cross = (a: Point, b: Point, c: Point) => (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]);
  function chain(ordered: Point[]) {
    const result: Point[] = [];
    for (const point of ordered) {
      while (result.length >= 2 && cross(result[result.length - 2], result[result.length - 1], point) <= 0) {
        result.pop();
      }
      result.push(point);
    }
    return result.slice(0, -1);
  }
  return [...chain(unique), ...chain([...unique].reverse())];
}

function separatingLine(left: Point[], right: Point[]) {
  const a = supportHull(left);
  const b = supportHull(right);
  const axes: Point[] = [
    [1, 0],
    [0, 1],
  ];
  for (const polygon of [a, b]) {
    for (let i = 0; i < polygon.length; i++) {
      const [x, y] = polygon[i];
      const [nextX, nextY] = polygon[(i + 1) % polygon.length];
      const dx = nextX - x;
      const dy = nextY - y;
      const length = Math.hypot(dx, dy);
      if (length === 0) continue;
      axes.push([-dy / length, dx / length]);
      if (polygon.length === 2) axes.push([dx / length, dy / length]);
    }
  }
  const projection = ([nx, ny]: Point, [x, y]: Point) => nx * x + ny * y;
  let best: { normal: Point; offset: number; gap: number } | undefined;
  for (const axis of axes) {
    const aValues = a.map((p) => projection(axis, p));
    const bValues = b.map((p) => projection(axis, p));
    const aMax = Math.max(...aValues);
    const bMin = Math.min(...bValues);
    const bMax = Math.max(...bValues);
    const aMin = Math.min(...aValues);
    const leftGap = bMin - aMax;
    const rightGap = aMin - bMax;
    if (leftGap > (best?.gap ?? EPS)) {
      best = { normal: axis, offset: (aMax + bMin) / 2, gap: leftGap };
    }
    if (rightGap > (best?.gap ?? EPS)) {
      best = { normal: [-axis[0], -axis[1]], offset: -(bMax + aMin) / 2, gap: rightGap };
    }
  }
  return best;
}

/** 左側の点を含む半平面を、重なり全体が入る矩形で有限化する。 */
function clipBox(box: Bounds, [nx, ny]: Point, offset: number): Polygon {
  const pad = EPS * 10;
  const corners: Point[] = [
    [box.minX - pad, box.minY - pad],
    [box.maxX + pad, box.minY - pad],
    [box.maxX + pad, box.maxY + pad],
    [box.minX - pad, box.maxY + pad],
  ];
  const side = ([x, y]: Point) => nx * x + ny * y - offset;
  const ring: Point[] = [];
  for (let i = 0; i < corners.length; i++) {
    const a = corners[i];
    const b = corners[(i + 1) % corners.length];
    const fa = side(a);
    const fb = side(b);
    if (fa <= 0) ring.push(a);
    if ((fa < 0 && fb > 0) || (fa > 0 && fb < 0)) {
      const t = fa / (fa - fb);
      ring.push([a[0] + t * (b[0] - a[0]), a[1] + t * (b[1] - a[1])]);
    }
  }
  return { regions: ring.length >= 3 ? [ring] : [], inverted: false };
}

function outlineTransform(outlines: ClusterOutline[]) {
  // ブール演算の許容誤差を投影座標の絶対スケールや原点に依存させない。
  const extent = bounds(outlines.flatMap(({ hull }) => hull));
  const span = Math.max(extent.maxX - extent.minX, extent.maxY - extent.minY) || 1;
  const normalize = ([x, y]: Point): Point => [(x - extent.minX) / span, (y - extent.minY) / span];
  const restore = ([x, y]: Point): Point => [x * span + extent.minX, y * span + extent.minY];
  return { normalize, restore };
}

export const clipScatterOutlines: OutlineClipper = (outlines) => {
  const result = new Map<string, Point[][]>();
  const stats = { overlaps: 0, oneSided: 0, straight: 0, remaining: 0, rejected: 0 };
  if (outlines.length < 2) return { result, stats };

  const { normalize, restore } = outlineTransform(outlines);
  const regions = outlines
    .map(({ id, hull, points }) => {
      const ring = hull.map(normalize);
      const area = Math.abs(signedArea(ring));
      const polygon: Polygon = { regions: [ring], inverted: false };
      return {
        id,
        polygon,
        box: bounds(ring),
        area,
        points,
        normalized: undefined as Point[] | undefined,
        changed: false,
      };
    })
    .filter(({ area }) => area > MIN_AREA)
    .sort((a, b) => a.box.minX - b.box.minX || (a.id < b.id ? -1 : a.id > b.id ? 1 : 0));

  const pairs: [number, number][] = [];
  regions.forEach(({ box }, i) => {
    for (let j = i + 1; j < regions.length; j++) {
      const other = regions[j].box;
      if (other.minX >= box.maxX) break;
      if (other.minY < box.maxY && box.minY < other.maxY) pairs.push([i, j]);
    }
  });

  for (const [i, j] of pairs) {
    const a = regions[i];
    const b = regions[j];
    try {
      const overlap = PolyBool.intersect(a.polygon, b.polygon);
      if (!hasArea(overlap)) continue;
      stats.overlaps++;
      const box = bounds(overlap.regions.flat());
      a.normalized ??= a.points.map(normalize);
      b.normalized ??= b.points.map(normalize);
      const pointsA = a.normalized;
      const pointsB = b.normalized;
      const occupiedA = pointsA.filter((point) => nearBox(point, box) && containsPoint(point, overlap.regions));
      const occupiedB = pointsB.filter((point) => nearBox(point, box) && containsPoint(point, overlap.regions));

      let nextA = a.polygon;
      let nextB = b.polygon;
      let split = false;
      if (occupiedA.length && occupiedB.length) {
        const line = separatingLine(occupiedA, occupiedB);
        if (!line) continue;
        const keepA = PolyBool.intersect(overlap, clipBox(box, line.normal, line.offset));
        const keepB = PolyBool.difference(overlap, keepA);
        nextA = PolyBool.difference(a.polygon, keepB);
        nextB = PolyBool.difference(b.polygon, keepA);
        split = true;
      } else if (occupiedA.length || (!occupiedB.length && b.area >= a.area)) {
        nextB = PolyBool.difference(b.polygon, overlap);
      } else {
        nextA = PolyBool.difference(a.polygon, overlap);
      }

      // 近接点や数値誤差で真の所属点が欠けた場合は、適用前の両領域を残す。
      if (
        (nextA !== a.polygon && (!hasArea(nextA) || !pointsA.every((p) => containsPoint(p, nextA.regions)))) ||
        (nextB !== b.polygon && (!hasArea(nextB) || !pointsB.every((p) => containsPoint(p, nextB.regions)))) ||
        hasArea(PolyBool.intersect(nextA, nextB))
      ) {
        stats.rejected++;
        continue;
      }
      a.changed ||= nextA !== a.polygon;
      b.changed ||= nextB !== b.polygon;
      a.polygon = nextA;
      b.polygon = nextB;
      if (split) stats.straight++;
      else stats.oneSided++;
    } catch {
      stats.rejected++;
    }
  }

  for (const [i, j] of pairs) {
    const a = regions[i];
    const b = regions[j];
    try {
      if (hasArea(PolyBool.intersect(a.polygon, b.polygon))) stats.remaining++;
    } catch {
      stats.remaining++;
    }
  }
  for (const { id, polygon, changed } of regions) {
    if (changed)
      result.set(
        id,
        polygon.regions.map((ring) => ring.map(restore)),
      );
  }
  return { result, stats };
};

export function inspectScatterOverlaps(outlines: ClusterOutline[]) {
  const clipped = clipScatterOutlines(outlines);
  if (outlines.length < 2) return { cases: [], clipped };
  const { normalize, restore } = outlineTransform(outlines);
  const polygon = (rings: Point[][]): Polygon => ({
    regions: rings.map((ring) => ring.map(normalize)),
    inverted: false,
  });
  const originals = outlines.map(({ hull }) => polygon([hull]));
  const finals = outlines.map(({ id, hull }) => polygon(clipped.result.get(id) ?? [hull]));
  const cases = [];
  for (let i = 0; i < outlines.length; i++) {
    for (let j = i + 1; j < outlines.length; j++) {
      const before = PolyBool.intersect(originals[i], originals[j]);
      if (!hasArea(before)) continue;
      const area = before.regions.reduce((sum, ring) => sum + Math.abs(signedArea(ring)), 0);
      const after = PolyBool.intersect(finals[i], finals[j]);
      const resolved = !hasArea(after);
      cases.push({
        ids: [outlines[i].id, outlines[j].id] as const,
        originalRings: before.regions.map((ring) => ring.map(restore)),
        remainingRings: resolved ? [] : after.regions.map((ring) => ring.map(restore)),
        area,
        resolved,
      });
    }
  }
  return { cases: cases.sort((a, b) => b.area - a.area), clipped };
}
