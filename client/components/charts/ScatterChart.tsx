import type { Argument, Cluster } from "@/type";
import { Box } from "@chakra-ui/react";
import { ChartCore } from "./ChartCore";

type Props = {
  clusterList: Cluster[];
  argumentList: Argument[];
  targetLevel: number;
  onHover?: () => void;
  showClusterLabels?: boolean;
  maxLabelWidth?: number;  // ラベルの最大横幅を指定するプロパティを追加
};

export function ScatterChart({
  clusterList,
  argumentList,
  targetLevel,
  onHover,
  showClusterLabels,
  maxLabelWidth = 10  // デフォルト値として10文字を設定
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
    "#00b4d8",
    "#e76f51",
    "#606c38",
    "#9d4edd",
    "#457b9d",
    "#bc6c25",
    "#2a9d8f",
    "#e07a5f",
    "#5e548e",
    "#81b29a",
    "#f4a261",
    "#9b5de5",
    "#f15bb5",
    "#00bbf9",
    "#98c1d9",
    "#84a59d",
    "#f28482",
    "#00afb9",
    "#cdb4db",
    "#fcbf49",
  ];
  const clusterColorMap = targetClusters.reduce(
    (acc, cluster, index) => {
      acc[cluster.id] = softColors[index % softColors.length];
      return acc;
    },
    {} as Record<string, string>,
  );

  // ラベルテキストを指定された幅で改行するヘルパー関数
  const wrapLabelText = (text: string, maxWidth: number): string => {
    if (!text || text.length <= maxWidth) return text;
    
    // HTML方式: span要素で幅を制限して自動改行させる
    // return `<span style="display:inline-block;max-width:${maxWidth * 10}px;word-wrap:break-word;">${text}</span>`;
    
    // テキスト分割方式: 指定の文字数ごとに改行を挿入
    const regex = new RegExp(`.{1,${maxWidth}}`, 'g');
    const lines = text.match(regex);
    return lines ? lines.join('<br>') : text;
  };

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
    <Box width="100%" height="100%" display="flex" flexDirection="column">
      <Box position="relative" flex="1">
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
        dragmode: "pan", // ドラッグによる移動（パン）を有効化
        annotations: showClusterLabels ? clusterData.map((data) => ({
          x: data.centerX,
          y: data.centerY,
          text: wrapLabelText(data.cluster.label, maxLabelWidth), // ラベルを折り返し処理
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
          width: maxLabelWidth * 14 + 5, // ラベルのフォントサイズに合わせる
          align: 'center', // テキストを中央揃えに
        })) : [],
        showlegend: false,
      }}
      useResizeHandler={true}
      style={{ width: "100%", height: "100%" }}
      config={{
        responsive: true,
        displayModeBar: "hover", // 操作時にツールバーを表示
        scrollZoom: true, // マウスホイールによるズームを有効化
        locale: "ja",
      }}
      onHover={onHover}
        />
      </Box>
    </Box>
  );
}
