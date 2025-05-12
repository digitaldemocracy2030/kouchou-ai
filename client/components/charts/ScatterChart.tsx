import type { Argument, Cluster } from "@/type";
import { Box } from "@chakra-ui/react";
import { ChartCore } from "./ChartCore";

type Props = {
  clusterList: Cluster[];
  argumentList: Argument[];
  targetLevel: number;
  onHover?: () => void;
  showClusterLabels?: boolean;
};

export function ScatterChart({
  clusterList,
  argumentList,
  targetLevel,
  onHover,
  showClusterLabels,
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

  const clusterColorMapA = targetClusters.reduce(
    (acc, cluster, index) => {
      const alpha = 0.8; // アルファ値を指定
      acc[cluster.id] = softColors[index % softColors.length] + Math.floor(alpha * 255).toString(16).padStart(2, '0');
      return acc;
    },
    {} as Record<string, string>,
  );

  const annotationLabelWidth = 228; // ラベルの最大横幅を指定
  const annotationFontsize = 14; // フォントサイズを指定

  // ラベルのテキストを折り返すための関数
  // ラベルのテキストを折り返すための関数
  const wrapLabelText = (text: string): string => {
    // 英語と日本語の文字数を考慮して、適切な長さで折り返す

    const alphabetWidth = 0.6; // 英字の幅

    let result = '';
    let currentLine = '';
    let currentLineLength = 0;
    
    // 文字ごとに処理
    for (let i = 0; i < text.length; i++) {
      const char = text[i];

      // 英字と日本語で文字幅を考慮
      // ASCIIの範囲（半角文字）かそれ以外（全角文字）かで幅を判定
      const charWidth = /[!-~]/.test(char) ? alphabetWidth : 1;
      const charLength = charWidth * annotationFontsize;
      currentLineLength += charLength;

      if (currentLineLength > annotationLabelWidth) {
        // 現在の行が最大幅を超えた場合、改行
        result += `${currentLine}<br>`;
        currentLine = char; // 新しい行の開始
        currentLineLength = charLength; // 新しい行の長さをリセット
      } else {
        currentLine += char; // 現在の行に文字を追加
      }
    }
    
    // 最後の行を追加
    if (currentLine) {
      result += `${currentLine}`;
    }
    
    return result;
  };

  const onUpdate = (_event: unknown) => {
    // Plotly単体で設定できないデザインを、onUpdateのタイミングでSVGをオーバーライドして解決する

    // アノテーションの角を丸にする
    const bgRound = 4
    try {
      document.querySelectorAll('g.annotation').forEach((g) => {
        const bg = g.querySelector('rect.bg');
        if (bg) {
          bg.setAttribute('rx', `${bgRound}px`);
          bg.setAttribute('ry', `${bgRound}px`);
        }
      });
    } catch (error) {
      console.error('アノテーション要素の角丸化に失敗しました:', error);
    }
  }

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
          showgrid: false,
        },
        yaxis: {
          zeroline: false,
          showticklabels: false,
          showgrid: false,
        },
        hovermode: "closest",
        dragmode: "pan", // ドラッグによる移動（パン）を有効化
        annotations: showClusterLabels ? clusterData.map((data) => ({
          x: data.centerX,
          y: data.centerY,
          text: wrapLabelText(data.cluster.label), // ラベルを折り返し処理
          showarrow: false,
          font: {
            color: "white",
            size: annotationFontsize,
            weight: 700,
          },
          bgcolor: clusterColorMapA[data.cluster.id], // 背景はアルファ付き
          borderpad: 10,
          width: annotationLabelWidth,
          align: 'left',
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
      onUpdate={onUpdate}
        />
      </Box>
    </Box>
  );
}
