import type { Argument, Cluster } from "@/type";
import { PlotHoverEvent } from "plotly.js";
import { ChartCore } from "./ChartCore";

type Props = {
  clusterList: Cluster[];
  argumentList: Argument[];
  targetLevel: number;
  onHover: (event: Readonly<PlotHoverEvent>) => void;
};

export function ScatterChart({
  clusterList,
  argumentList,
  targetLevel,
  onHover
}: Props) {
  const targetClusters = clusterList.filter(
    (cluster) => cluster.level === targetLevel,
  );
  const softColors = [
    "#7ac943",
    "#3fa9f5",
    "#ff7997",
    "#e0dd02",
    "#d6410f",
    "#b39647",
    "#7cccc3",
    "#a147e6",
    "#ff6b6b",
    "#4ecdc4",
    "#ffbe0b",
    "#fb5607",
    "#8338ec",
    "#3a86ff",
    "#ff006e",
    "#8ac926",
    "#1982c4",
    "#6a4c93",
    "#f72585",
    "#7209b7",
  ];
  const clusterColorMap = targetClusters.reduce(
    (acc, cluster, index) => {
      acc[cluster.id] = softColors[index % softColors.length];
      return acc;
    },
    {} as Record<string, string>,
  );

  // クラスタごとのデータを構築
  const clusterData = targetClusters.map((cluster) => {
    const clusterArguments = argumentList.filter((arg) =>
      arg.cluster_ids.includes(cluster.id),
    );
    const xValues = clusterArguments.map((arg) => arg.x);
    const yValues = clusterArguments.map((arg) => arg.y);
    const texts = clusterArguments.map(
      (arg) =>
        `<b>${cluster.label}</b><br>${arg.argument.replace(/(.{30})/g, "$1<br />")}`,
    );

    // クラスタ中心の座標を計算
    const centerX = xValues.reduce((sum, val) => sum + val, 0) / xValues.length;
    const centerY = yValues.reduce((sum, val) => sum + val, 0) / yValues.length;

    return {
      cluster,
      xValues,
      yValues,
      texts,
      centerX,
      centerY,
    };
  });

  return (
    <ChartCore
      data={clusterData.map((data) => ({
        x: data.xValues,
        y: data.yValues,
        mode: "markers",
        marker: {
          size: 7,
          color: clusterColorMap[data.cluster.id],
        },
        type: "scatter",
        text: data.texts,
        hoverinfo: "text",
        hoverlabel: {
          align: "left",
          bgcolor: "white",
          bordercolor: clusterColorMap[data.cluster.id],
          font: {
            size: 12,
            color: "#333",
          },
        },
      }))}
      layout={{
        margin: { l: 0, r: 0, b: 0, t: 0 },
        xaxis: {
          zeroline: false,
          showticklabels: false,
        },
        yaxis: {
          zeroline: false,
          showticklabels: false,
        },
        hovermode: "closest",
        annotations: clusterData.map((data) => ({
          x: data.centerX,
          y: data.centerY,
          text: data.cluster.label,
          showarrow: false,
          font: {
            color: "white",
            size: 14,
            weight: 700,
          },
          bgcolor: clusterColorMap[data.cluster.id],
          opacity: 0.8,
          bordercolor: clusterColorMap[data.cluster.id],
          borderpad: 4,
          borderwidth: 1,
        })),
        showlegend: false,
      }}
      useResizeHandler={true}
      style={{ width: "100%", height: "100%" }}
      config={{
        responsive: true,
        displayModeBar: false,
        locale: "ja",
      }}
      onHover={onHover}
    />
  );
}
