import type { Argument, Cluster } from "@/type";
import type { Data, Layout } from "plotly.js";
import { clusterColor } from "./clusterColors";

export type Point = [number, number];
export type ClusterOutline = { id: string; hull: Point[]; points: Point[] };
export type OutlineClipper = (outlines: ClusterOutline[]) => {
  result: Map<string, Point[][]>;
  stats: { overlaps: number; oneSided: number; straight: number; remaining: number; rejected: number };
};

export function makeScatterOutlineLayer(
  clusters: Cluster[],
  argumentsByCluster: ReadonlyMap<string, Argument[]>,
  clipper?: OutlineClipper,
) {
  const outlines = clusters.flatMap((cluster, index) => {
    const args = argumentsByCluster.get(cluster.id);
    if (!args || args.length < 3) return [];
    const points: Point[] = args.map(({ x, y }) => [x, y]);
    const hull = convexHull(points);
    return hull.length < 3 ? [] : [{ id: cluster.id, label: cluster.label, index, hull, points }];
  });
  const clipped = clipper?.(outlines);
  const traces: Data[] = [];
  const shapes: NonNullable<Layout["shapes"]> = [];

  for (const { id, label, index, hull } of outlines) {
    const color = clusterColor(index);
    const rings = clipped?.result.get(id);
    if (rings) {
      // evenodd は外周・飛び地・穴を一つのパスで扱える。
      const path = rings
        .map((ring) => [...ring.map(([x, y], i) => `${i === 0 ? "M" : "L"} ${x},${y}`), "Z"].join(" "))
        .join(" ");
      shapes.push({
        type: "path",
        path,
        xref: "x",
        yref: "y",
        fillrule: "evenodd",
        fillcolor: `${color}33`,
        line: { color, width: 1.5 },
        layer: "below",
        name: label,
      });
      continue;
    }
    traces.push({
      x: [...hull.map((p) => p[0]), hull[0][0]],
      y: [...hull.map((p) => p[1]), hull[0][1]],
      mode: "lines",
      fill: "toself",
      fillcolor: `${color}33`,
      line: { color, width: 1.5 },
      type: "scatter",
      hoveron: "fills",
      hoverinfo: "text",
      text: label,
      hoverlabel: { bgcolor: color, bordercolor: color, font: { color: "white", size: 13 } },
      showlegend: false,
    });
  }
  return { traces, shapes, stats: clipped?.stats };
}

/** 凸包計算（Gift wrapping アルゴリズム） */
function convexHull(points: Point[]): Point[] {
  if (points.length < 3) return points;

  // 最も左下の点を開始点とする
  let start = 0;
  for (let i = 1; i < points.length; i++) {
    if (points[i][0] < points[start][0] || (points[i][0] === points[start][0] && points[i][1] < points[start][1])) {
      start = i;
    }
  }

  // current からの二乗距離を計算するヘルパー
  const distanceSquared = (a: [number, number], b: [number, number]) => {
    const dx = a[0] - b[0];
    const dy = a[1] - b[1];
    return dx * dx + dy * dy;
  };

  const hull: Point[] = [];
  let current = start;

  do {
    hull.push(points[current]);
    let next = (current + 1) % points.length;
    for (let i = 0; i < points.length; i++) {
      if (i === current) continue;
      const cross =
        (points[next][0] - points[current][0]) * (points[i][1] - points[current][1]) -
        (points[next][1] - points[current][1]) * (points[i][0] - points[current][0]);
      if (cross < 0) {
        // より外側にある点を採用
        next = i;
      } else if (cross === 0) {
        // 3点が一直線上にある場合は、current からより遠い点を採用
        if (distanceSquared(points[current], points[i]) > distanceSquared(points[current], points[next])) {
          next = i;
        }
      }
    }
    current = next;
  } while (current !== start && hull.length < points.length);

  return hull;
}
