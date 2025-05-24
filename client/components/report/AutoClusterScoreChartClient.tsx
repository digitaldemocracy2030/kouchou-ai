"use client";

import { Box, Text } from "@chakra-ui/react";
import Plot from "react-plotly.js";

type DataPoint = {
  label: string; // 例: "top-3" / "bottom-15"
  score: number;
};

type Props = {
  data: DataPoint[];
  bestTop: number;
  bestBottom: number;
  durationSec: number;
};

export default function AutoClusterScoreChartClient({ data, bestTop, bestBottom, durationSec }: Props) {
  // x軸ラベルを数値だけに変換 & 上下層分類
  const simplified = data.map((d) => {
    const parts = d.label.split("-");
    const layer = parts[0]; // top or bottom
    const num = Number(parts[1]);
    return { ...d, labelNum: num, layer };
  });

  const topData = simplified.filter((d) => d.layer === "top");
  const bottomData = simplified.filter((d) => d.layer === "bottom");

  return (
    <Box w="100%" maxW="750px" mx="auto" mb={8}>
      <Text fontWeight="bold" mb={2}>
        意見グループ数ごとの「まとまりの良さ（シルエットスコア）」推移
      </Text>
      <Text mb={2}>グループ内の固まりがよく、他のグループと離れていると高い数値になります</Text>
      <Plot
        data={[
          {
            x: topData.map((d) => d.labelNum),
            y: topData.map((d) => d.score),
            type: "scatter",
            mode: "lines+markers",
            name: "統合ラベル数（上層）",
            line: { color: "#3182CE" },
          },
          {
            x: bottomData.map((d) => d.labelNum),
            y: bottomData.map((d) => d.score),
            type: "scatter",
            mode: "lines+markers",
            name: "初期ラベル数（下層）",
            line: { color: "#38A169" },
          },
        ]}
        layout={{
          margin: { t: 30, b: 40, l: 50, r: 30 },
          xaxis: {
            title: { text: "グループ数" },
            tickmode: "linear",
            dtick: 1,
          },
          yaxis: { title: { text: "シルエットスコア" } },
          height: 300,
          shapes: [
            {
              type: "line",
              x0: bestTop,
              x1: bestTop,
              y0: 0,
              y1: 1,
              xref: "x",
              yref: "paper",
              line: { color: "#3182CE", width: 2, dash: "dot" },
            },
            {
              type: "line",
              x0: bestBottom,
              x1: bestBottom,
              y0: 0,
              y1: 1,
              xref: "x",
              yref: "paper",
              line: { color: "#38A169", width: 2, dash: "dot" },
            },
          ],
          annotations: [
            {
              x: bestTop,
              y: 1,
              xref: "x",
              yref: "paper",
              text: "選択",
              showarrow: false,
              font: { color: "#3182CE", size: 12 },
              yanchor: "bottom",
            },
            {
              x: bestBottom,
              y: 1,
              xref: "x",
              yref: "paper",
              text: "選択",
              showarrow: false,
              font: { color: "#38A169", size: 12 },
              yanchor: "bottom",
            },
          ],
        }}
        config={{ displayModeBar: false }}
      />
      <Text mt={4} fontSize="sm" color="gray.600">
        試行時間: {durationSec.toFixed(2)} 秒
      </Text>
    </Box>
  );
}
