import { Tooltip } from "@/components/ui/tooltip";
import { groupArgumentsByCluster, splitArgumentsByFilter, toIdSet } from "@/lib/argumentIndex";
import { wrapJapaneseText } from "@/lib/wrapJapaneseText";
import type { Argument, Cluster, Config } from "@/type";
import { Box, Flex, Icon, IconButton, Text } from "@chakra-ui/react";
import { CircleHelp } from "lucide-react";
import type { Annotation, Data, Layout, PlotMouseEvent } from "plotly.js";
import { useCallback, useEffect, useMemo, useRef } from "react";
import { ChartCore } from "./ChartCore";

// クラスタ配色のパレット。参照を安定させて clusterColorMap などの useMemo を効かせるため、
// コンポーネント外（モジュールスコープ）の定数として保持する。
const SOFT_COLORS = [
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

// 意見を持たないクラスタに使う空配列（参照を共有するので変更しないこと）
const NO_ARGUMENTS: Argument[] = [];

// フィルタで全点が除外された（plot 上でグレー表示される）クラスタの凡例 swatch 色。
// plot 側の notMatchingData と同じ色にして視覚的に整合させる。
const FILTERED_SWATCH_COLOR = "#cccccc";

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
  // クラスタ上の点をクリックした時に、そのクラスタIDを通知する（連動文章・一覧のハイライト用）
  onSelectCluster?: (clusterId: string) => void;
  // 濃い意見グループが属する第一階層クラスタの帰属を可視化するか（scatterDensity モードで true）
  showParentAttribution?: boolean;
};

/**
 * 意見の座標と指定階層のクラスタを散布図で表示する。
 * 絞り込み対象外の意見も灰色で残し、元の分布との比較を可能にする。
 * ソースへの遷移はレポート設定に従い、Plotly Cloudへの送信導線は表示しない。
 */
export function ScatterChart({
  clusterList,
  argumentList,
  targetLevel,
  onHover,
  showClusterLabels,
  filteredArgumentIds, // フィルター済みIDリスト（フィルター条件に合致する引数のID）
  config,
  showConvexHull,
  onSelectCluster,
  showParentAttribution,
}: Props) {
  // 全ての引数を表示するため、argumentListをそのまま使用
  // フィルター条件に合致しないものは後で灰色表示する
  const allArguments = argumentList;

  // フィルタ判定は Set で行う。配列の includes だと全意見 N 件 × フィルタ ID |F| 件の比較になり、大規模レポートで固まる。
  const filteredIdSet = useMemo(() => toIdSet(filteredArgumentIds), [filteredArgumentIds]);
  // cluster_id → 意見の索引。クラスタごとに全意見を filter すると、クラスタ数 × 意見数の走査になるため 1 回だけ作る。
  const argumentsByCluster = useMemo(() => groupArgumentsByCluster(allArguments), [allArguments]);
  const argumentsOf = (clusterId: string) => argumentsByCluster.get(clusterId) ?? NO_ARGUMENTS;

  // clusterList.filter() は毎レンダリング新しい配列参照を生成するため、
  // hullTraces の useMemo deps に含める際に参照が安定するよう useMemo でメモ化する
  const targetClusters = useMemo(
    () => clusterList.filter((cluster) => cluster.level === targetLevel),
    [clusterList, targetLevel],
  );
  const clusterColorMap = useMemo(
    () =>
      targetClusters.reduce(
        (acc, cluster, index) => {
          acc[cluster.id] = SOFT_COLORS[index % SOFT_COLORS.length];
          return acc;
        },
        {} as Record<string, string>,
      ),
    [targetClusters],
  );

  const clusterColorMapA = useMemo(
    () =>
      targetClusters.reduce(
        (acc, cluster, index) => {
          const alpha = 0.8; // アルファ値を指定
          acc[cluster.id] =
            SOFT_COLORS[index % SOFT_COLORS.length] +
            Math.floor(alpha * 255)
              .toString(16)
              .padStart(2, "0");
          return acc;
        },
        {} as Record<string, string>,
      ),
    [targetClusters],
  );

  // 濃い意見グループ（最深階層の表示対象クラスタ）が、どの第一階層（level === 1）クラスタに
  // 属するかを `parent` チェーンを辿って解決する。帰属情報は既存の Cluster データ構造
  // （cluster.parent）だけで辿れるため、新たなデータ追加は不要。
  const clusterById = useMemo(() => {
    const map = new Map<string, Cluster>();
    for (const cluster of clusterList) map.set(cluster.id, cluster);
    return map;
  }, [clusterList]);

  const resolveTopAncestor = useCallback(
    (cluster: Cluster): Cluster | undefined => {
      let current: Cluster | undefined = cluster;
      const visited = new Set<string>(); // 万一の循環参照でも無限ループしないよう防御
      while (current && current.level > 1) {
        if (visited.has(current.id)) return undefined;
        visited.add(current.id);
        if (!current.parent) break;
        current = clusterById.get(current.parent);
      }
      return current && current.level === 1 ? current : undefined;
    },
    [clusterById],
  );

  // 帰属可視化用のデータ。各濃いグループの親ラベル（hover 用）と、
  // 第一階層クラスタごとにグルーピングした凡例データ（色対応つき）を作る。
  const parentAttribution = useMemo(() => {
    if (!showParentAttribution) return null;

    // plot のグレー化判定と整合させるため、フィルタ条件に合致する引数を 1 件以上持つ
    // クラスタ ID の集合を 1 パスで作る。plot 側の allElementsFiltered
    // （filteredArgumentIds && (matching.length === 0 || cluster.allFiltered)）と同条件。
    const clusterIdsWithMatching = new Set<string>();
    if (filteredIdSet) {
      for (const arg of allArguments) {
        if (!filteredIdSet.has(arg.arg_id)) continue;
        for (const clusterId of arg.cluster_ids) clusterIdsWithMatching.add(clusterId);
      }
    }

    const labelByClusterId = new Map<string, string>();
    const groupMap = new Map<
      string,
      {
        parentId: string;
        parentLabel: string;
        members: { id: string; label: string; color: string; filteredOut: boolean }[];
      }
    >();
    for (const cluster of targetClusters) {
      const top = resolveTopAncestor(cluster);
      const parentLabel = top?.label ?? "不明";
      labelByClusterId.set(cluster.id, parentLabel);
      const key = top?.id ?? "__unknown__";
      // このクラスタの点が plot 上で全てグレー表示になる（表示対象が 0 件）か
      const filteredOut =
        Boolean(filteredIdSet) && (!clusterIdsWithMatching.has(cluster.id) || Boolean(cluster.allFiltered));
      if (!groupMap.has(key)) groupMap.set(key, { parentId: key, parentLabel, members: [] });
      groupMap.get(key)?.members.push({
        id: cluster.id,
        label: cluster.label,
        color: filteredOut ? FILTERED_SWATCH_COLOR : clusterColorMap[cluster.id],
        filteredOut,
      });
    }
    return { labelByClusterId, groups: Array.from(groupMap.values()) };
  }, [showParentAttribution, targetClusters, resolveTopAncestor, clusterColorMap, allArguments, filteredIdSet]);

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

  // フィルター条件に合致するアイテムと合致しないアイテムの分割結果を、クラスタごとに 1 回だけ計算して使い回す
  // （散布図のトレースとラベル注釈の判定で同じ分割を 2 回走らせないため）
  const splitByClusterId = new Map<string, ReturnType<typeof splitArgumentsByFilter>>();
  const separateDataByFilter = (cluster: Cluster) => {
    let split = splitByClusterId.get(cluster.id);
    if (!split) {
      split = splitArgumentsByFilter(argumentsOf(cluster.id), filteredIdSet);
      splitByClusterId.set(cluster.id, split);
    }
    return split;
  };

  // 各クラスターのデータを生成（フィルター対象外を背面に、フィルター対象を前面に描画するため分離）
  const clusterDataSets = targetClusters.map((cluster) => {
    // クラスターに属するすべての引数を取得（フィルター状況に関係なく）
    const allClusterArguments = argumentsOf(cluster.id);

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
                ? notMatching.map((arg) => ({ arg_id: arg.arg_id, url: arg.url, cluster_id: cluster.id }))
                : allClusterArguments.map((arg) => ({ arg_id: arg.arg_id, url: arg.url, cluster_id: cluster.id })),
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
              const argumentText = wrapJapaneseText(arg.argument, 30);
              const urlText = config?.enable_source_link && arg.url ? "<br><b>🔗 クリックしてソースを見る</b>" : "";
              const parentText = parentAttribution
                ? `<br>所属: ${parentAttribution.labelByClusterId.get(cluster.id) ?? "不明"}`
                : "";
              return `<b>${cluster.label}</b>${parentText}<br>${argumentText}${urlText}`;
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
            customdata: matching.map((arg) => ({ arg_id: arg.arg_id, url: arg.url, cluster_id: cluster.id })),
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
      const clusterArguments = dataSet.allClusterArguments;
      if (clusterArguments.length > 0) {
        result.push({
          x: clusterArguments.map((arg) => arg.x),
          y: clusterArguments.map((arg) => arg.y),
          mode: "markers",
          marker: {
            size: 7,
            color: clusterColorMap[dataSet.cluster.id],
          },
          text: clusterArguments.map((arg) => {
            const parentText = parentAttribution
              ? `<br>所属: ${parentAttribution.labelByClusterId.get(dataSet.cluster.id) ?? "不明"}`
              : "";
            return `<b>${dataSet.cluster.label}</b>${parentText}<br>${wrapJapaneseText(arg.argument, 30)}`;
          }),
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
          customdata: clusterArguments.map((arg) => ({
            arg_id: arg.arg_id,
            url: arg.url,
            cluster_id: dataSet.cluster.id,
          })),
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
  // 上流の安定した参照（targetClusters / argumentsByCluster）を deps とする。
  const hullTraces = useMemo(() => {
    if (!showConvexHull) return [];
    return targetClusters.flatMap((cluster, index) => {
      const clusterArguments = argumentsByCluster.get(cluster.id) ?? NO_ARGUMENTS;
      if (clusterArguments.length < 3) return [];
      const hull = convexHull(clusterArguments.map((arg) => [arg.x, arg.y]));
      if (hull.length < 3) return [];
      const color = SOFT_COLORS[index % SOFT_COLORS.length];
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
  }, [showConvexHull, targetClusters, argumentsByCluster]);

  // 凸包を最背面に挿入（scatter点の下に描画）
  const allPlotData = [...hullTraces, ...plotData];

  // アノテーションの設定
  const annotations: Partial<Annotation>[] = showClusterLabels
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

  // 散布図の操作方法を示すヒント。クリックでソースを開く挙動はソースリンク有効時のみ案内する。
  const operationHint = (
    <Box fontSize="xs" lineHeight="1.6">
      <Text fontWeight="bold" mb={1}>
        散布図の操作方法
      </Text>
      <Text>・ドラッグ: 表示位置を移動（パン）</Text>
      <Text>・マウスホイール / ピンチ: 拡大・縮小</Text>
      <Text>・右上ツールバー: 拡大・移動・初期表示へリセット</Text>
      <Text>・点にカーソルを合わせる: 意見の内容を表示</Text>
      {config?.enable_source_link && <Text>・点をクリック: 元のソースを開く</Text>}
    </Box>
  );

  return (
    <Box width="100%" height="100%" display="flex" flexDirection="column">
      <Box position="relative" flex="1" minH={0} ref={chartWrapperRef}>
        <Box position="absolute" top="8px" left="8px" zIndex={2}>
          <Tooltip content={operationHint} showArrow openDelay={0} closeDelay={150} contentProps={{ maxW: "260px" }}>
            <IconButton
              aria-label="散布図の操作方法を表示"
              size="xs"
              variant="ghost"
              color="gray.500"
              bg="whiteAlpha.800"
              _hover={{ bg: "whiteAlpha.900", color: "gray.700" }}
            >
              <Icon as={CircleHelp} />
            </IconButton>
          </Tooltip>
        </Box>
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
            showSendToCloud: false, // Plotly Cloudへの送信導線は表示しない
            scrollZoom: true, // マウスホイールによるズームを有効化
            locale: "ja",
          }}
          onUpdate={onUpdate}
          onClick={(data: PlotMouseEvent) => {
            try {
              const point = data.points?.[0];
              const customData = point?.customdata as unknown as
                | { arg_id: string; url?: string; cluster_id?: string }
                | undefined;

              // クリックしたクラスタを連動文章・一覧へ通知する（ソースリンクの有無に関わらず動作する）
              if (customData?.cluster_id) {
                onSelectCluster?.(customData.cluster_id);
              }

              // 以降のソース遷移はレポート設定で有効な場合のみ行う
              if (!config?.enable_source_link) return;

              // customdataから直接argumentの情報を取得
              if (customData) {
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
      {parentAttribution && parentAttribution.groups.length > 0 && (
        <Box flexShrink={0} px={3} py={2} borderTop="1px solid #eee" maxH="140px" overflowY="auto" bg="#fafafa">
          <Text fontSize="xs" fontWeight="bold" color="gray.600" mb={1}>
            濃い意見グループの第一階層クラスタへの帰属
          </Text>
          <Flex wrap="wrap" gap={3}>
            {parentAttribution.groups.map((group) => (
              <Box key={group.parentId} border="1px solid #e2e8f0" borderRadius="md" px={2} py={1} bg="white">
                <Text fontSize="xs" fontWeight="bold" mb={1} color="gray.700">
                  {group.parentLabel}
                </Text>
                <Flex wrap="wrap" gap={2}>
                  {group.members.map((member) => (
                    <Flex key={member.id} align="center" gap={1} opacity={member.filteredOut ? 0.5 : 1}>
                      <Box w="10px" h="10px" borderRadius="sm" flexShrink={0} bg={member.color} />
                      <Text fontSize="xs" color="gray.600">
                        {member.label}
                        {member.filteredOut ? "（非表示）" : ""}
                      </Text>
                    </Flex>
                  ))}
                </Flex>
              </Box>
            ))}
          </Flex>
        </Box>
      )}
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
