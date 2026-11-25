"use client";

import { ScatterChart } from "@/components/charts/ScatterChart";
import { makeScatterOutlineLayer } from "@/components/charts/scatterOutlines";
import { groupArgumentsByCluster } from "@/lib/argumentIndex";
import type { Argument, Cluster, Config } from "@/type";
import type { Data, Layout, PlotlyHTMLElement, ScatterglData } from "plotly.js";
import { useEffect, useRef, useState } from "react";
import { ScatterOverlapComparison } from "./ScatterOverlapComparison";
import { clipScatterOutlines } from "./clipScatterOutlines";

type Strategy = "convex" | "clip";

export function ScatterOutlinePreview({
  arguments: arguments_,
  clusters,
  config,
  dataset,
  measure,
  compare,
  initialPair,
}: {
  arguments: Argument[];
  clusters: Cluster[];
  config: Config;
  dataset: "example" | "polis";
  measure: boolean;
  compare: boolean;
  initialPair?: string;
}) {
  const [strategy, setStrategy] = useState<Strategy>("convex");
  const chart = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!measure) return;
    const topClusters = clusters.filter((cluster) => cluster.level === 1);
    const byCluster = groupArgumentsByCluster(arguments_);
    const snapshots = new Map<Strategy, { data: Data[]; layout: Partial<Layout> }>();
    const bench = {
      geometry(mode: Strategy) {
        const start = performance.now();
        const layer = makeScatterOutlineLayer(
          topClusters,
          byCluster,
          mode === "clip" ? clipScatterOutlines : undefined,
        );
        return { ms: performance.now() - start, stats: layer.stats };
      },
      capture(mode: Strategy) {
        const plot = chart.current?.querySelector<PlotlyHTMLElement>(".js-plotly-plot");
        if (!plot?.data) throw new Error("散布図の描画が完了していません");
        const { data, layout } = structuredClone({ data: plot.data, layout: plot.layout });
        const width = plot.clientWidth;
        const height = plot.clientHeight;
        snapshots.set(mode, { data, layout: { ...layout, width, height, autosize: false } });
        const markers = data.filter((trace): trace is Partial<ScatterglData> => trace.type === "scattergl");
        return {
          width,
          height,
          shapes: layout.shapes?.length ?? 0,
          markerCoordinates: markers.map(({ x, y }) => ({ x, y })),
          points: new Set(
            markers.flatMap((trace) => {
              const info = (trace.customdata ?? []) as unknown as { arg_id: string }[];
              return info.map(({ arg_id }) => arg_id);
            }),
          ).size,
        };
      },
      async draw(mode: Strategy) {
        const snapshot = snapshots.get(mode);
        if (!snapshot) throw new Error("先に描画するデータを取得してください");
        const Plotly = await import("plotly.js/lib/core");
        const { data, layout } = structuredClone(snapshot);
        const replay = document.createElement("div");
        replay.style.cssText = "position:fixed;inset:0 auto auto 0;z-index:1000;background:white";
        document.body.append(replay);
        try {
          const start = performance.now();
          const plot = await Plotly.newPlot(replay, data, layout, {
            responsive: false,
            displayModeBar: "hover",
            scrollZoom: true,
            locale: "ja",
          });
          const drawMs = performance.now() - start;
          await new Promise<void>((done) => requestAnimationFrame(() => requestAnimationFrame(() => done())));
          const axis = Reflect.get(plot, "_fullLayout").xaxis.range as [number, number];
          const inset = (axis[1] - axis[0]) / 10;
          const zoomStart = performance.now();
          await Plotly.relayout(plot, {
            xaxis: { ...layout.xaxis, range: [axis[0] + inset, axis[1] - inset], autorange: false },
          });
          return { drawMs, zoomMs: performance.now() - zoomStart };
        } finally {
          Plotly.purge(replay);
          replay.remove();
        }
      },
    };
    const scope = window as Window & { scatterOutlineBenchmark?: typeof bench };
    scope.scatterOutlineBenchmark = bench;
    return () => {
      scope.scatterOutlineBenchmark = undefined;
    };
  }, [arguments_, clusters, measure]);

  const datasetLink = (value: string) => `/dev/scatter-outlines/?data=${value}${compare ? "" : "&view=overview"}`;
  return (
    <main style={{ padding: 16 }}>
      <h1>散布図の輪郭比較</h1>
      <p>{arguments_.length.toLocaleString("ja-JP")} 点・最上位クラスタ</p>
      <nav aria-label="レポート" style={{ display: "flex", flexWrap: "wrap", gap: 16 }}>
        <a href={datasetLink("example")} aria-current={dataset === "example" ? "page" : undefined}>
          同梱サンプル
        </a>
        <a href={datasetLink("polis")} aria-current={dataset === "polis" ? "page" : undefined}>
          Polis の例
        </a>
      </nav>
      <p>
        <a href={`/dev/scatter-outlines/?data=${dataset}${compare ? "&view=overview" : ""}`}>
          {compare ? "全体表示で見る" : "重なりを同じ範囲で拡大比較する"}
        </a>
      </p>
      {compare ? (
        <ScatterOverlapComparison
          key={dataset}
          arguments={arguments_}
          clusters={clusters}
          config={config}
          initialPair={initialPair}
        />
      ) : (
        <>
          <fieldset style={{ display: "flex", gap: 16, marginBlock: 12 }}>
            <legend>輪郭の描き方</legend>
            <label>
              <input
                type="radio"
                name="outline"
                checked={strategy === "convex"}
                onChange={() => setStrategy("convex")}
              />
              現行の凸包
            </label>
            <label>
              <input type="radio" name="outline" checked={strategy === "clip"} onChange={() => setStrategy("clip")} />
              重なりを切り抜く
            </label>
          </fieldset>
          <div ref={chart} style={{ height: "min(68vh, 600px)", minHeight: 300 }}>
            <ScatterChart
              argumentList={arguments_}
              clusterList={clusters}
              config={config}
              targetLevel={1}
              showConvexHull
              showClusterLabels
              prototypeClipper={strategy === "clip" ? clipScatterOutlines : undefined}
            />
          </div>
        </>
      )}
    </main>
  );
}
