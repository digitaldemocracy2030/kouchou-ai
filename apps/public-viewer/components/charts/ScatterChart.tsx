// filepath: c:\Users\shinta\Documents\GitHub\kouchou-ai\client\components\charts\ScatterChart.tsx
import type { Argument, Cluster, Config } from "@/type";
import { Box } from "@chakra-ui/react";
import type { Annotations, Data, Layout, PlotMouseEvent } from "plotly.js";
import { ChartCore } from "./ChartCore";

type Props = {
  clusterList: Cluster[];
  argumentList: Argument[];
  targetLevel: number;
  onHover?: () => void;
  showClusterLabels?: boolean;
  // フィルター適用後の引数IDのリストを受け取り、フィルターに該当しないポイントの表示を変更する
  filteredArgumentIds?: string[];
  config?: Config; // ソースリンク機能の有効/無効を制御するため
};

export function ScatterChart({
  clusterList,
  argumentList,
  targetLevel,
  onHover,
  showClusterLabels,
  filteredArgumentIds, // フィルター済みIDリスト（フィルター条件に合致する引数のID）
  config,
}: Props) {
  // 全ての引数を表示するため、argumentListをそのまま使用
  // フィルター条件に合致しないものは後で灰色表示する
  const allArguments = argumentList;

  const targetClusters = clusterList.filter((cluster) => cluster.level === targetLevel);
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
      acc[cluster.id] =
        softColors[index % softColors.length] +
        Math.floor(alpha * 255)
          .toString(16)
          .padStart(2, "0");
      return acc;
    },
    {} as Record<string, string>,
  );

  const annotationLabelWidth = 228; // ラベルの最大横幅を指定
  const annotationFontsize = 14; // フォントサイズを指定

  // ラベルのテキストを折り返すための関数
  const wrapLabelText = (text: string): string => {
    // 英語と日本語の文字数を考慮して、適切な長さで折り返す

    const alphabetWidth = 0.6; // 英字の幅

    let result = "";
    let currentLine = "";
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
    // Plotly単体で設定できないデザインを、onUpdateのタイミングでHTMLをオーバーライドして解決する

    // アノテーションの角を丸にする
    const bgRound = 4;
    try {
      for (const g of document.querySelectorAll("g.annotation")) {
        const bg = g.querySelector("rect.bg");
        if (bg) {
          bg.setAttribute("rx", `${bgRound}px`);
          bg.setAttribute("ry", `${bgRound}px`);
        }
      }
    } catch (error) {
      console.error("アノテーション要素の角丸化に失敗しました:", error);
    }

    // プロット操作用アイコンのエリアを「全画面終了」ボタンの下に移動する
    avoidModBarCoveringShrinkButton();
  };

  // フィルターが適用されている場合、フィルター条件に合致するアイテムと合致しないアイテムを分離
  const separateDataByFilter = (cluster: Cluster) => {
    if (!filteredArgumentIds) {
      // フィルターなしの場合は通常表示
      const clusterArguments = allArguments.filter((arg) => arg.cluster_ids.includes(cluster.id));
      return {
        matching: clusterArguments,
        notMatching: [] as Argument[],
      };
    }

    // フィルター条件に合致するアイテム（前面に表示）
    const matchingArguments = allArguments.filter(
      (arg) => arg.cluster_ids.includes(cluster.id) && filteredArgumentIds.includes(arg.arg_id),
    );

    // フィルター条件に合致しないアイテム（背面に表示）
    const notMatchingArguments = allArguments.filter(
      (arg) => arg.cluster_ids.includes(cluster.id) && !filteredArgumentIds.includes(arg.arg_id),
    );

    return {
      matching: matchingArguments,
      notMatching: notMatchingArguments,
    };
  };

  // 各クラスターのデータを生成（フィルター対象外を背面に、フィルター対象を前面に描画するため分離）
  const clusterDataSets = targetClusters.map((cluster) => {
    // クラスターに属するすべての引数を取得（フィルター状況に関係なく）
    const allClusterArguments = allArguments.filter((arg) => arg.cluster_ids.includes(cluster.id));

    // クラスター中心はフィルター状況に関わらず、すべての要素から計算
    const allXValues = allClusterArguments.map((arg) => arg.x);
    const allYValues = allClusterArguments.map((arg) => arg.y);

    const centerX = allXValues.length > 0 ? allXValues.reduce((sum, val) => sum + val, 0) / allXValues.length : 0;
    const centerY = allYValues.length > 0 ? allYValues.reduce((sum, val) => sum + val, 0) / allYValues.length : 0;

    // フィルター適用後の表示用データを分離
    const { matching, notMatching } = separateDataByFilter(cluster);

    // フィルターが適用されている場合に、クラスター内の全要素がフィルターされていても表示する
    // @ts-ignore allFilteredプロパティが存在する前提で処理（TypeScript型定義に追加済み）
    const allElementsFiltered = filteredArgumentIds && (matching.length === 0 || cluster.allFiltered);

    const notMatchingData =
      notMatching.length > 0 || allElementsFiltered
        ? {
            x: notMatching.length > 0 ? notMatching.map((arg) => arg.x) : allClusterArguments.map((arg) => arg.x),
            y: notMatching.length > 0 ? notMatching.map((arg) => arg.y) : allClusterArguments.map((arg) => arg.y),
            mode: "markers",
            marker: {
              size: 7,
              color: Array(notMatching.length > 0 ? notMatching.length : allClusterArguments.length).fill("#cccccc"), // グレー表示
              opacity: Array(notMatching.length > 0 ? notMatching.length : allClusterArguments.length).fill(0.5), // 半透明
            },
            text: Array(notMatching.length > 0 ? notMatching.length : allClusterArguments.length).fill(""), // ホバーテキストなし
            type: "scattergl",
            hoverinfo: "skip", // ホバー表示を無効化
            showlegend: false,
            // argumentのメタデータを埋め込み
            customdata:
              notMatching.length > 0
                ? notMatching.map((arg) => ({ arg_id: arg.arg_id, url: arg.url }))
                : allClusterArguments.map((arg) => ({ arg_id: arg.arg_id, url: arg.url })),
          }
        : null;

    // フィルター対象のアイテム（前面に描画）
    const matchingData =
      matching.length > 0
        ? {
            x: matching.map((arg) => arg.x),
            y: matching.map((arg) => arg.y),
            mode: "markers",
            marker: {
              size: 10, // 統一サイズでシンプルに
              color: Array(matching.length).fill(clusterColorMap[cluster.id]),
              opacity: Array(matching.length).fill(1), // 不透明
              line: config?.enable_source_link
                ? {
                    width: 2,
                    color: "#ffffff",
                  }
                : undefined,
            },
            text: matching.map((arg) => {
              const argumentText = arg.argument.replace(/(.{30})/g, "$1<br />");
              const urlText = config?.enable_source_link && arg.url ? "<br><b>🔗 クリックしてソースを見る</b>" : "";
              return `<b>${cluster.label}</b><br>${argumentText}${urlText}`;
            }),
            type: "scattergl",
            hoverinfo: "text",
            hovertemplate: "%{text}<extra></extra>",
            hoverlabel: {
              align: "left" as const,
              bgcolor: "white",
              bordercolor: clusterColorMap[cluster.id],
              font: {
                size: 12,
                color: "#333",
              },
            },
            showlegend: false,
            // argumentのメタデータを埋め込み
            customdata: matching.map((arg) => ({ arg_id: arg.arg_id, url: arg.url })),
          }
        : null;

    return {
      cluster,
      notMatchingData,
      matchingData,
      centerX,
      centerY,
    };
  });

  // 描画用のデータセットを作成
  const plotData = clusterDataSets.flatMap((dataSet) => {
    const result = [];

    // フィルター対象外のデータ（背面に描画）
    if (dataSet.notMatchingData) {
      result.push(dataSet.notMatchingData);
    }

    // フィルター対象のデータ（前面に描画）
    if (dataSet.matchingData) {
      result.push(dataSet.matchingData);
    }

    // フィルターがない場合の通常表示
    if (!filteredArgumentIds) {
      const clusterArguments = allArguments.filter((arg) => arg.cluster_ids.includes(dataSet.cluster.id));
      if (clusterArguments.length > 0) {
        result.push({
          x: clusterArguments.map((arg) => arg.x),
          y: clusterArguments.map((arg) => arg.y),
          mode: "markers",
          marker: {
            size: 7,
            color: clusterColorMap[dataSet.cluster.id],
          },
          text: clusterArguments.map(
            (arg) => `<b>${dataSet.cluster.label}</b><br>${arg.argument.replace(/(.{30})/g, "$1<br />")}`,
          ),
          type: "scattergl",
          hoverinfo: "text",
          hoverlabel: {
            align: "left" as const,
            bgcolor: "white",
            bordercolor: clusterColorMap[dataSet.cluster.id],
            font: {
              size: 12,
              color: "#333",
            },
          },
          showlegend: false,
          // argumentのメタデータを埋め込み
          customdata: clusterArguments.map((arg) => ({ arg_id: arg.arg_id, url: arg.url })),
        });
      }
    }

    return result;
  });

  // アノテーションの設定
  const annotations: Partial<Annotations>[] = showClusterLabels
    ? clusterDataSets.map((dataSet) => {
        // フィルターされていても背景色を維持（灰色のクラスターでもラベルは元の色で表示）
        // @ts-ignore allFilteredプロパティが存在する前提で処理（TypeScript型定義に追加済み）
        const isAllFiltered =
          filteredArgumentIds &&
          (separateDataByFilter(dataSet.cluster).matching.length === 0 || dataSet.cluster.allFiltered);
        const bgColor = isAllFiltered
          ? clusterColorMapA[dataSet.cluster.id].replace(/[0-9a-f]{2}$/i, "cc") // クラスター全体がフィルターされた場合も薄くする
          : clusterColorMapA[dataSet.cluster.id];

        return {
          x: dataSet.centerX,
          y: dataSet.centerY,
          text: wrapLabelText(dataSet.cluster.label), // ラベルを折り返し処理
          showarrow: false,
          font: {
            color: "white",
            size: annotationFontsize,
            weight: 700,
          },
          bgcolor: bgColor,
          borderpad: 10,
          width: annotationLabelWidth,
          align: "left" as const,
        };
      })
    : [];

  return (
    <Box width="100%" height="100%" display="flex" flexDirection="column">
      <Box position="relative" flex="1">
        <ChartCore
          data={plotData as unknown as Data[]}
          layout={
            {
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
              annotations,
              showlegend: false,
            } as Partial<Layout>
          }
          useResizeHandler={true}
          style={{ width: "100%", height: "100%", cursor: config?.enable_source_link ? "pointer" : "default" }}
          config={{
            responsive: true,
            displayModeBar: "hover", // 操作時にツールバーを表示
            scrollZoom: true, // マウスホイールによるズームを有効化
            locale: "ja",
          }}
          onHover={onHover}
          onUpdate={onUpdate}
          onClick={(data: PlotMouseEvent) => {
            if (!config?.enable_source_link) return;

            try {
              const point = data.points?.[0];

              // customdataから直接argumentの情報を取得
              if (point?.customdata) {
                const customData = point.customdata as unknown as { arg_id: string; url?: string };

                if (customData.url) {
                  window.open(customData.url, "_blank", "noopener,noreferrer");
                } else {
                  // customdataにURLがない場合、argumentListから検索
                  const matchedArgument = argumentList.find((arg) => arg.arg_id === customData.arg_id);
                  if (matchedArgument?.url) {
                    window.open(matchedArgument.url, "_blank", "noopener,noreferrer");
                  } else {
                    console.log("No URL found for argument:", customData.arg_id);
                  }
                }
              } else {
                console.log("No customdata found in clicked point");
              }
            } catch (error) {
              console.error("Error in click handler:", error);
            }
          }}
        />
      </Box>
    </Box>
  );
}

function avoidModBarCoveringShrinkButton(): void {
  const modeBarContainer = document.querySelector(".modebar-container") as HTMLElement;
  if (!modeBarContainer) return;
  const modeBar = modeBarContainer.children[0] as HTMLElement;
  const shrinkButton = document.getElementById("fullScreenButtons");
  if (!modeBar || !shrinkButton) return;
  const modeBarPos = modeBar.getBoundingClientRect();
  const btnPos = shrinkButton.getBoundingClientRect();
  const isCovered = !(
    btnPos.top > modeBarPos.bottom ||
    btnPos.bottom < modeBarPos.top ||
    btnPos.left > modeBarPos.right ||
    btnPos.right < modeBarPos.left
  );
  if (!isCovered) return;

  const diff = btnPos.bottom - modeBarPos.top;
  modeBarContainer.style.top = `${Number.parseInt(modeBarContainer.style.top.slice(0, -2)) + diff + 10}px`;
}
