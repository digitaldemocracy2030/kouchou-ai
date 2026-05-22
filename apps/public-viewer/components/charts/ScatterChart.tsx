import type { Argument, Cluster, Config } from "@/type";
import { Box } from "@chakra-ui/react";
import type { Annotations, Data, Layout, PlotMouseEvent } from "plotly.js";
import { useCallback, useEffect, useMemo, useRef } from "react";
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
  showConvexHull?: boolean; // クラスターの凸包を表示するか
};

export function ScatterChart({
  clusterList,
  argumentList,
  targetLevel,
  onHover,
  showClusterLabels,
  filteredArgumentIds, // フィルター済みIDリスト（フィルター条件に合致する引数のID）
  config,
  showConvexHull,
}: Props) {
  // 全ての引数を表示するため、argumentListをそのまま使用
  // フィルター条件に合致しないものは後で灰色表示する
  const allArguments = argumentList;

  // clusterList.filter() は毎レンダリング新しい配列参照を生成するため、
  // hullTraces の useMemo deps に含める際に参照が安定するよう useMemo でメモ化する
  const targetClusters = useMemo(
    () => clusterList.filter((cluster) => cluster.level === targetLevel),
    [clusterList, targetLevel],
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

  // ホバー中にアノテーション（クラスタラベル）を非表示にするための参照
  const chartWrapperRef = useRef<HTMLDivElement>(null);
  const hideTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const onHoverRef = useRef(onHover);
  onHoverRef.current = onHover;

  // arg_id → アノテーションインデックスのマッピング（イベントハンドラからref経由で参照）
  const argToAnnotationIndexRef = useRef<Map<string, number[]>>(new Map());
  const argToAnnotationIndex = useMemo(() => {
    const map = new Map<string, number[]>();
    for (const arg of allArguments) {
      const indices: number[] = [];
      for (let i = 0; i < targetClusters.length; i++) {
        if (arg.cluster_ids.includes(targetClusters[i].id)) {
          indices.push(i);
        }
      }
      if (indices.length > 0) map.set(arg.arg_id, indices);
    }
    return map;
  }, [allArguments, targetClusters]);
  argToAnnotationIndexRef.current = argToAnnotationIndex;

  // Plotly gd 要素の参照とハンドラを保持し、差し替え・アンマウント時にクリーンアップする
  type PlotlyGd = HTMLElement & {
    on?: (event: string, handler: (data: unknown) => void) => void;
    removeListener?: (event: string, handler: (data: unknown) => void) => void;
  };
  const boundGdRef = useRef<PlotlyGd | null>(null);
  const hoverHandlerRef = useRef<((data: unknown) => void) | null>(null);
  const unhoverHandlerRef = useRef<((data: unknown) => void) | null>(null);

  /** 旧 gd からリスナーを解除する */
  const detachHoverListeners = useCallback(() => {
    const oldGd = boundGdRef.current;
    if (!oldGd?.removeListener) return;
    if (hoverHandlerRef.current) oldGd.removeListener("plotly_hover", hoverHandlerRef.current);
    if (unhoverHandlerRef.current) oldGd.removeListener("plotly_unhover", unhoverHandlerRef.current);
    hoverHandlerRef.current = null;
    unhoverHandlerRef.current = null;
    boundGdRef.current = null;
  }, []);

  useEffect(() => {
    return () => {
      // アンマウント時: タイマーとイベントリスナーをクリーンアップ
      if (hideTimerRef.current) clearTimeout(hideTimerRef.current);
      detachHoverListeners();
    };
  }, [detachHoverListeners]);

  // react-plotly.js の onUpdate は (figure, gd) で呼ばれる。
  // gd は Plotly が .on() メソッドを付与した HTMLElement。
  const onUpdate = (_figure: unknown, graphDiv?: Readonly<HTMLElement>) => {
    // Plotly単体で設定できないデザインを、onUpdateのタイミングでHTMLをオーバーライドして解決する

    applyScatterChartDomOverrides();

    // Plotly gd 要素に hover/unhover イベントを直接登録
    // graphDiv が差し替わった場合は旧リスナーを解除して再登録する
    const gd = graphDiv as PlotlyGd | undefined;
    if (boundGdRef.current && boundGdRef.current !== gd) {
      detachHoverListeners();
    }
    if (gd?.on && !boundGdRef.current) {
      const handleHover = (eventData: unknown) => {
        if (hideTimerRef.current) clearTimeout(hideTimerRef.current);
        const ed = eventData as { points?: Array<{ customdata?: { arg_id?: string } }> } | undefined;
        const point = ed?.points?.[0];
        const argId = point?.customdata?.arg_id;
        const wrapper = chartWrapperRef.current;
        if (argId && wrapper) {
          const annotationEls = wrapper.querySelectorAll("g.annotation");
          // まず全ラベルを復帰してから、該当クラスタのラベルだけ非表示にする
          for (const g of annotationEls) {
            (g as HTMLElement).style.opacity = "1";
            (g as HTMLElement).style.transition = "opacity 0.15s ease";
          }
          const annotationIndices = argToAnnotationIndexRef.current.get(argId) ?? [];
          for (const idx of annotationIndices) {
            const el = annotationEls[idx] as HTMLElement | undefined;
            if (el) {
              el.style.opacity = "0";
              el.style.transition = "opacity 0.15s ease";
            }
          }
        }
        onHoverRef.current?.();
      };
      const handleUnhover = () => {
        if (hideTimerRef.current) clearTimeout(hideTimerRef.current);
        hideTimerRef.current = setTimeout(() => {
          const wrapper = chartWrapperRef.current;
          if (!wrapper) return;
          for (const g of wrapper.querySelectorAll("g.annotation")) {
            (g as HTMLElement).style.opacity = "1";
            (g as HTMLElement).style.transition = "opacity 0.15s ease";
          }
        }, 300);
      };
      gd.on("plotly_hover", handleHover);
      gd.on("plotly_unhover", handleUnhover);
      hoverHandlerRef.current = handleHover;
      unhoverHandlerRef.current = handleUnhover;
      boundGdRef.current = gd;
    }
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
      allClusterArguments,
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

  // 凸包トレースの生成（scatterAll / scatterDetail モード用）
  // NOTE: hull trace は意図的に type: "scatter"（SVG）を使用している。
  // hoveron: "fills" はSVGレイヤーのみでサポートされており、
  // scattergl（WebGL）では動作しない。また Plotly の z-order により
  // SVGトレースはWebGLトレースの背面に自動配置されるため、scatter点の
  // 下に凸包が描画される。この SVG/WebGL 混在は意図的な設計である。
  // Gift wrapping は O(nh) のため、入力が変わらない限り再計算しないよう useMemo でメモ化する。
  // clusterDataSets / clusterColorMap は毎レンダリング再生成されるので、
  // 上流の安定した参照（targetClusters / argumentList / filteredArgumentIds）を deps とする。
  const hullTraces = useMemo(() => {
    if (!showConvexHull) return [];
    return targetClusters.flatMap((cluster, index) => {
      const clusterArguments = argumentList.filter((arg) => arg.cluster_ids.includes(cluster.id));
      if (clusterArguments.length < 3) return [];
      const hull = convexHull(clusterArguments.map((arg) => [arg.x, arg.y]));
      if (hull.length < 3) return [];
      const color = softColors[index % softColors.length];
      return [
        {
          x: [...hull.map((p) => p[0]), hull[0][0]],
          y: [...hull.map((p) => p[1]), hull[0][1]],
          mode: "lines",
          fill: "toself",
          fillcolor: `${color}33`,
          line: { color, width: 1.5 },
          type: "scatter",
          hoveron: "fills",
          hoverinfo: "text",
          text: cluster.label,
          hoverlabel: {
            bgcolor: color,
            bordercolor: color,
            font: { color: "white", size: 13 },
          },
          showlegend: false,
        },
      ];
    });
  }, [showConvexHull, targetClusters, argumentList]);

  // 凸包を最背面に挿入（scatter点の下に描画）
  const allPlotData = [...hullTraces, ...plotData];

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
      <Box position="relative" flex="1" ref={chartWrapperRef}>
        <ChartCore
          data={allPlotData as unknown as Data[]}
          layout={
            {
              uirevision: "scatter", // ズーム・パン状態をデータ更新後も保持する
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

/** 凸包計算（Gift wrapping アルゴリズム） */
function convexHull(points: [number, number][]): [number, number][] {
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

  const hull: [number, number][] = [];
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

export function applyScatterChartDomOverrides(): void {
  // アノテーションの角を丸くする
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

  // hover modebar のコンテナは全体を覆うため、ボタン本体以外は pointer event を食わないようにする
  const modeBarContainer = document.querySelector(".modebar-container") as HTMLElement | null;
  const modeBar = modeBarContainer?.children[0] as HTMLElement | undefined;
  if (modeBarContainer) {
    modeBarContainer.style.pointerEvents = "none";
  }
  if (modeBar) {
    modeBar.style.pointerEvents = "auto";
  }

  // プロット操作用アイコンのエリアを「全画面終了」ボタンの下に移動する
  avoidModeBarCoveringShrinkButton(modeBarContainer, modeBar);
}

export function avoidModeBarCoveringShrinkButton(
  modeBarContainer: HTMLElement | null,
  modeBar?: HTMLElement | null,
): void {
  const shrinkButton = document.getElementById("fullScreenButtons");
  const effectiveModeBar = modeBar ?? (modeBarContainer?.children[0] as HTMLElement | undefined);
  if (!modeBarContainer || !effectiveModeBar || !shrinkButton) return;
  const modeBarPos = effectiveModeBar.getBoundingClientRect();
  const btnPos = shrinkButton.getBoundingClientRect();
  const isCovered = !(
    btnPos.top > modeBarPos.bottom ||
    btnPos.bottom < modeBarPos.top ||
    btnPos.left > modeBarPos.right ||
    btnPos.right < modeBarPos.left
  );
  if (!isCovered) return;

  const diff = btnPos.bottom - modeBarPos.top;
  const currentTop = Number.parseInt(modeBarContainer.style.top.slice(0, -2)) || 0;
  modeBarContainer.style.top = `${currentTop + diff + 10}px`;
}
