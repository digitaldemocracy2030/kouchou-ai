"use client";

import { ScatterChart } from "@/components/charts/ScatterChart";
import { clusterColor } from "@/components/charts/clusterColors";
import { type Point, getClusterOutlines, outlinePath } from "@/components/charts/scatterOutlines";
import { groupArgumentsByCluster } from "@/lib/argumentIndex";
import type { Argument, Cluster, Config } from "@/type";
import { useCallback, useMemo, useState } from "react";
import styles from "./ScatterOverlapComparison.module.css";
import { clipScatterOutlines, inspectScatterOverlaps } from "./clipScatterOutlines";
import { clipScatterOutlinesWithVoronoi } from "./clipScatterOutlinesWithVoronoi";

type Method = "clip" | "voronoi";

function frameFor(rings: Point[][], clusterIds: readonly string[]) {
  const points = rings.flat();
  const xs = points.map(([x]) => x);
  const ys = points.map(([, y]) => y);
  const left = Math.min(...xs);
  const right = Math.max(...xs);
  const bottom = Math.min(...ys);
  const top = Math.max(...ys);
  const centerX = (left + right) / 2;
  const centerY = (bottom + top) / 2;
  const width = Math.max(right - left, 1.5 * (top - bottom)) * 1.45;
  const height = width / 1.5;
  return {
    x: [centerX - width / 2, centerX + width / 2] as [number, number],
    y: [centerY - height / 2, centerY + height / 2] as [number, number],
    clusterIds,
    guidePath: outlinePath(rings),
  };
}

export function ScatterOverlapComparison({
  arguments: arguments_,
  clusters,
  config,
  initialPair,
  initialMethod,
}: { arguments: Argument[]; clusters: Cluster[]; config: Config; initialPair?: string; initialMethod: Method }) {
  const [method, setMethod] = useState(initialMethod);
  const { cases, clipped, labels } = useMemo(() => {
    const topClusters = clusters.filter(({ level }) => level === 1);
    const outlines = getClusterOutlines(topClusters, groupArgumentsByCluster(arguments_));
    const clipper = method === "voronoi" ? clipScatterOutlinesWithVoronoi : clipScatterOutlines;
    const inspection = inspectScatterOverlaps(outlines, clipper);
    return {
      ...inspection,
      labels: new Map(topClusters.map(({ id, label }, index) => [id, { label, color: clusterColor(index) }])),
    };
  }, [arguments_, clusters, method]);
  const clipper = useCallback(() => clipped, [clipped]);
  const [pair, setPair] = useState(initialPair);
  const keyOf = (ids: readonly string[]) => ids.join(":");
  const selected = cases.find(({ ids }) => keyOf(ids) === pair) ?? cases.find(({ resolved }) => resolved) ?? cases[0];
  const viewport = useMemo(() => selected && frameFor(selected.originalRings, selected.ids), [selected]);
  if (!selected || !viewport) return <p>重なっている輪郭の組がありません。</p>;

  const resolvedCount = cases.filter(({ resolved }) => resolved).length;
  const selectedStatus = selected.resolved ? "この組の重なりは解消" : "この組の重なりは残存";
  function selectPair(key: string) {
    setPair(key);
    const url = new URL(window.location.href);
    url.searchParams.set("pair", key);
    window.history.replaceState(null, "", url);
  }

  function selectMethod(next: Method) {
    if (!selected) return;
    const key = keyOf(selected.ids);
    setPair(key);
    setMethod(next);
    const url = new URL(window.location.href);
    url.searchParams.set("pair", key);
    url.searchParams.set("method", next);
    window.history.replaceState(null, "", url);
  }

  return (
    <>
      <div className={styles.picker}>
        <fieldset>
          <legend>試作の分割方法</legend>
          <label>
            <input type="radio" name="partition" checked={method === "clip"} onChange={() => selectMethod("clip")} />
            切り抜き・直線分割
          </label>
          <label>
            <input
              type="radio"
              name="partition"
              checked={method === "voronoi"}
              onChange={() => selectMethod("voronoi")}
            />
            局所ボロノイを追加
          </label>
        </fieldset>
        <label htmlFor="outline-pair">拡大する組</label>
        <select id="outline-pair" value={keyOf(selected.ids)} onChange={(e) => selectPair(e.target.value)}>
          {[
            { title: `解消（${resolvedCount}組）`, resolved: true },
            { title: `残存（${cases.length - resolvedCount}組）`, resolved: false },
          ].map(({ title, resolved }) => (
            <optgroup key={title} label={title}>
              {cases
                .filter((item) => item.resolved === resolved)
                .map(({ ids }) => (
                  <option key={keyOf(ids)} value={keyOf(ids)}>
                    {ids.map((id) => labels.get(id)?.label ?? id).join(" × ")}
                  </option>
                ))}
            </optgroup>
          ))}
        </select>
      </div>
      <section data-testid="outline-pair-comparison" aria-label="同じ範囲で拡大比較">
        <h2 aria-live="polite">{selectedStatus}</h2>
        <div className={styles.legend}>
          {selected.ids.map((id) => (
            <span key={id}>
              <span
                aria-hidden="true"
                className={styles.legendKey}
                style={{ backgroundColor: labels.get(id)?.color }}
              />
              {labels.get(id)?.label ?? id}
            </span>
          ))}
        </div>
        <p>点線は現行の重なり範囲。右の灰色は試作で残った重なりです。</p>
        <div className={styles.panels}>
          {[
            { title: "現行の凸包", clip: false },
            { title: method === "voronoi" ? "局所ボロノイを追加" : "切り抜き・直線分割", clip: true },
          ].map(({ title, clip }) => (
            <figure key={title}>
              <figcaption>{title}</figcaption>
              <div className={styles.plot}>
                <ScatterChart
                  argumentList={arguments_}
                  clusterList={clusters}
                  config={config}
                  targetLevel={1}
                  showConvexHull
                  prototypeClipper={clip ? clipper : undefined}
                  prototypeViewport={
                    clip && !selected.resolved
                      ? { ...viewport, remainingPath: outlinePath(selected.remainingRings) }
                      : viewport
                  }
                />
              </div>
            </figure>
          ))}
        </div>
      </section>
    </>
  );
}
