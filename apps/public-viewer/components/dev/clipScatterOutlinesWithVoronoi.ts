import { Delaunay } from "d3-delaunay";
import PolyBool, { type Polygon } from "polybooljs";
import type { Point } from "../charts/scatterOutlines";
import { type Bounds, makeScatterOutlineClipper } from "./clipScatterOutlines";

function mergeCells(cells: Polygon[], start: number, end: number): Polygon {
  if (end === start + 1) return cells[start];
  const middle = Math.floor((start + end) / 2);
  return PolyBool.union(mergeCells(cells, start, middle), mergeCells(cells, middle, end));
}

function partitionOverlap(a: Point[], b: Point[], box: Bounds) {
  const distinct = (points: Point[]) => new Map(points.map((point) => [point.join(","), point]));
  const uniqueA = distinct(a);
  const uniqueB = distinct(b);
  for (const key of uniqueB.keys()) {
    // 両クラスタの点が同じ座標にある場合は所属を保てる境界を決められない。
    if (uniqueA.has(key)) return undefined;
  }

  // 片側のセルだけを結合し、もう片側には重なりの残りを渡す。
  const side = uniqueA.size <= uniqueB.size ? "a" : "b";
  const first = side === "a" ? uniqueA : uniqueB;
  const last = side === "a" ? uniqueB : uniqueA;
  const sites = [...first.values(), ...last.values()];
  const pad = 1e-8;
  const voronoi = Delaunay.from(sites).voronoi([box.minX - pad, box.minY - pad, box.maxX + pad, box.maxY + pad]);
  const cells: Polygon[] = [];
  for (let index = 0; index < first.size; index++) {
    const ring = voronoi.cellPolygon(index);
    if (!ring || ring.length < 4) return undefined;
    cells.push({ regions: [ring.slice(0, -1)], inverted: false });
  }
  return { polygon: mergeCells(cells, 0, cells.length), side, sites: sites.length } as const;
}

export const clipScatterOutlinesWithVoronoi = makeScatterOutlineClipper(partitionOverlap);
