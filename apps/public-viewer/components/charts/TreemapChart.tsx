import { toIdSet } from "@/lib/argumentIndex";
import { useLanguage } from "@/lib/i18n/LanguageContext";
import { type Messages, getMessages } from "@/lib/i18n/messages";
import { wrapJapaneseText } from "@/lib/wrapJapaneseText";
import type { Argument, Cluster } from "@/type";
import type { Layout, TreemapData } from "plotly.js";
import { useCallback, useMemo, useRef } from "react";
import { ChartCore } from "./ChartCore";

type Props = {
  clusterList: Cluster[];
  argumentList: Argument[];
  onHover?: () => void;
  level: string;
  onTreeZoom: (level: string) => void;
  filteredArgumentIds?: string[]; // 追加: フィルター済みID
};

/**
 * ツリーマップに渡す trace と layout を作る（純関数）。
 * TreemapChart は入力が変わったときだけこれを呼び、無関係な再描画で全意見を加工し直さない。
 */
export function buildTreemapFigure(
  clusterList: Cluster[],
  argumentList: Argument[],
  level: string,
  filteredArgumentIds: string[] | undefined,
  messages: Messages = getMessages("ja"),
): { data: Partial<TreemapData>; layout: Partial<Layout> } {
  // フィルタリングが有効かどうかをチェック
  const isFilteringActive = !!filteredArgumentIds;
  // フィルタ判定は Set で行う（配列の includes だと全意見 N 件 × フィルタ ID |F| 件の比較になる）
  const filteredIdSet = toIdSet(filteredArgumentIds);

  // フィルターされていない場合は全ての引数を表示
  const convertedArgumentList = argumentList.map((arg) => {
    const converted = convertArgumentToCluster(arg);

    // フィルターが適用されていて、フィルター結果に含まれない場合はグレーにする
    if (filteredIdSet && !filteredIdSet.has(arg.arg_id)) {
      // フィルターに該当しないものは灰色表示用のプロパティを追加
      return {
        ...converted,
        filtered: true, // フィルターで除外されたフラグ
      };
    }
    return converted;
  });

  // フィルター適用後の各クラスタの件数を計算
  const clusterCounts: Record<string, number> = {};

  // 初期化: すべてのクラスタの件数を0にセット
  for (const cluster of clusterList) {
    clusterCounts[cluster.id] = 0;
  }

  // フィルター適用後の引数を使ってカウント
  for (const arg of argumentList) {
    // フィルターが適用されていて、引数がフィルター対象でない場合はスキップ
    if (filteredIdSet && !filteredIdSet.has(arg.arg_id)) {
      continue;
    }

    // 各クラスタIDに対して件数を増やす
    for (const clusterId of arg.cluster_ids) {
      if (clusterCounts[clusterId] !== undefined) {
        clusterCounts[clusterId]++;
      }
    }
  }

  // 葉（意見）は、表示中の階層から見える範囲のものだけを渡す（見えない葉まで渡すと、Plotly が全意見分の slice を作って重い）
  const leafArgumentList = selectTreemapLeaves(clusterList, convertedArgumentList, level);

  const list = [{ ...clusterList[0], parent: "" }, ...clusterList.slice(1), ...leafArgumentList];
  const ids = list.map((node) => node.id);
  const labels = list.map((node) => {
    return node.id === level ? wrapJapaneseText(node.label, 50) : wrapJapaneseText(node.label, 15);
  });
  const parents = list.map((node) => node.parent);
  const values = list.map((node) => {
    // クラスターノードの場合、フィルター後の件数を使用
    if (clusterCounts[node.id] !== undefined) {
      return isFilteringActive ? clusterCounts[node.id] : node.value;
    }
    // 引数ノードの場合、フィルター状態に基づいて値を決定
    // @ts-ignore filtered プロパティを追加したので無視
    return node.filtered ? 0 : 1; // フィルター対象外なら0、そうでなければ1
  });
  const customdata = list.map((node) => {
    let takeaway = wrapJapaneseText(node.takeaway, 15);

    // クラスターノードの場合、フィルター情報を追加
    if (clusterCounts[node.id] !== undefined && isFilteringActive) {
      const originalCount = node.value;
      const filteredCount = clusterCounts[node.id];

      if (filteredCount < originalCount) {
        takeaway = `${takeaway}<br><br>${messages.originalCount}: ${originalCount}<br>${messages.afterFilterCount}: ${filteredCount}`;
      }
    }

    // @ts-ignore filtered プロパティを追加したので無視
    return node.filtered
      ? "" // フィルター対象外はホバー表示しない
      : takeaway;
  });

  // フィルター状態によって色を変更
  const colors = list.map((node) => {
    // @ts-ignore filtered プロパティを追加したので無視
    return node.filtered ? "#cccccc" : ""; // フィルターに該当しないものはグレー、それ以外はデフォルト色
  });

  // すべてのアイテムでホバー表示を有効にする
  // ホバーテンプレートでカスタムデータを使用するため、hoverinfo は不要になった

  const data: Partial<TreemapData> = {
    type: "treemap",
    ids: ids,
    labels: labels,
    parents: parents,
    values: values,
    customdata: customdata,
    level: level,
    branchvalues: "total",
    marker: {
      colors: colors,
      line: {
        width: 1,
        color: "white",
      },
    },
    // フィルター対象外のノードではホバー表示を無効にする
    hoverinfo: "text",
    hovertemplate: "%{customdata}<extra></extra>",
    hoverlabel: {
      align: "left",
    },
    texttemplate: isFilteringActive ? messages.treemapTextFiltered : messages.treemapText,
    maxdepth: TREEMAP_MAX_DEPTH,
    pathbar: {
      thickness: 28,
    },
  };

  const layout: Partial<Layout> = {
    margin: { l: 10, r: 10, b: 10, t: 30 },
    colorway: [
      "#b3daa1",
      "#f5c5d7",
      "#d5e5f0",
      "#fbecc0",
      "#80b8ca",
      "#dabeed",
      "#fad1af",
      "#fbb09d",
      "#a6e3ae",
      "#f1e4d6",
    ],
  };

  return { data, layout };
}

/**
 * クラスタと意見を、指定された表示階層を起点にツリーマップで描画する。
 * 絞り込み結果を件数と色に反映し、クリックやパスバーでの階層移動を
 * onTreeZoomへ通知して、React側の表示階層と説明を同期する。
 */
export function TreemapChart({ clusterList, argumentList, onHover, level, onTreeZoom, filteredArgumentIds }: Props) {
  const { language, messages } = useLanguage();
  // react-plotly は data・layout・config のどれかの参照が変わると Plotly.react で描き直すので、どれも memo して渡す
  const figure = useMemo(
    () => buildTreemapFigure(clusterList, argumentList, level, filteredArgumentIds, messages),
    [clusterList, argumentList, level, filteredArgumentIds, messages],
  );
  // Plotly の設定。参照を安定させて、再描画のたびに Plotly.react が走らないようにする（言語の切替時だけ作り直す）
  const plotlyConfig = useMemo(() => ({ responsive: true, displayModeBar: false, locale: language }), [language]);
  const data = useMemo(() => [figure.data], [figure]);

  // react-plotly はイベントハンドラを、描画データが変わって描き直すときにしか付け替えない。
  // 描画データを memo したので、ハンドラは ref 経由で最新の props を読む。
  const latestHandlersRef = useRef({ onHover, onTreeZoom });
  latestHandlersRef.current = { onHover, onTreeZoom };
  const handleHover = useCallback(() => {
    const { onHover: currentOnHover } = latestHandlersRef.current;
    currentOnHover ? currentOnHover() : null;
    darkenPathbar();
  }, []);
  const handleTreemapClick = useCallback((event: { nextLevel?: string }) => {
    // パスバーで戻る場合もReact側の表示階層と説明を同期する。
    if (event.nextLevel !== undefined) latestHandlersRef.current.onTreeZoom(event.nextLevel);
    return false;
  }, []);

  return (
    <ChartCore
      data={data}
      layout={figure.layout}
      useResizeHandler={true}
      style={{ width: "100%", height: "100%" }}
      config={plotlyConfig}
      onUpdate={darkenPathbar}
      onUnhover={darkenPathbar}
      onHover={handleHover}
      onTreemapClick={handleTreemapClick}
    />
  );
}

// ツリーマップの trace に渡す maxdepth（表示中の階層から何段下まで描くか）
const TREEMAP_MAX_DEPTH = 2;

/**
 * ツリーマップに渡す葉（意見ノード）を、表示中の階層 level から見えるものに絞る。
 *
 * - Plotly は level を根にした部分木で深さを数え、深さ < maxdepth のノードだけを描く（maxdepth: 2 なら level 自身とその子）。
 *   したがって意見ノードが見えるのは、親クラスタが level のときだけ。
 * - 見えない意見も Plotly は slice として作る（座標を一点に潰すだけ）ので、件数が多いと開く・戻るが数秒かかる。
 * - ただし、見えないクラスタから子を全部外すと、そのクラスタが「葉」扱いになって色（depthfade）が変わる。
 *   そこで見えないクラスタには代表の意見を 1 件だけ残す。代表は、Plotly が値の降順に並べたときに最後に来るもの
 *   （フィルタ後の値が 0 の意見があればその最後、無ければ最後の意見）にする。最後の slice の色を基準にする
 *   darkenPathbar の結果も変えないため。
 * - level がクラスタでない（想定外の値）ときは絞らない。
 *
 * 入力の並びは保つ。
 */
export function selectTreemapLeaves<T extends { id: string; parent: string; filtered?: boolean }>(
  clusterList: Cluster[],
  leaves: T[],
  level: string,
): T[] {
  const parentById = new Map<string, string>();
  for (const cluster of clusterList) parentById.set(cluster.id, cluster.parent);
  // level 自身はルート（parent が空）でも Map に入る
  if (!parentById.has(level)) return leaves;

  const isVisible = (leaf: T) => {
    // 意見ノードの深さ（level からの段数）= 親クラスタまでの段数 + 1。深さ < maxdepth なら描かれる
    let clusterId: string | undefined = leaf.parent;
    for (let depth = 1; depth < TREEMAP_MAX_DEPTH; depth++) {
      if (clusterId === level) return true;
      clusterId = clusterId === undefined ? undefined : parentById.get(clusterId);
    }
    return false;
  };

  const representativeByParent = new Map<string, T>();
  const visible = new Set<T>();
  for (const leaf of leaves) {
    if (isVisible(leaf)) {
      visible.add(leaf);
      continue;
    }
    const current = representativeByParent.get(leaf.parent);
    // 値 0（フィルタで除外）の意見は値 1 の意見より後ろに並ぶので、0 のものを優先し、同じ値なら後のものにする
    if (!current || leaf.filtered || !current.filtered) representativeByParent.set(leaf.parent, leaf);
  }
  for (const leaf of representativeByParent.values()) visible.add(leaf);
  return leaves.filter((leaf) => visible.has(leaf));
}

function convertArgumentToCluster(argument: Argument): Cluster {
  return {
    level: 3,
    id: argument.arg_id,
    label: argument.argument,
    takeaway: "",
    value: 1,
    parent: argument.cluster_ids[argument.cluster_ids.length - 1],
    density_rank_percentile: 0,
  };
}

export function darkenPathbar() {
  // plotly は hover / unhover のイベントを、ラベルや強調の後片付けより前に呼ぶ。
  // ここで例外を投げると後片付けが飛ばされるので、色付けに失敗しても外へは投げない
  try {
    const panels = document.querySelectorAll(".treemap > .slice > .surface");
    if (!panels.length) return;
    const leafColor = getColor(panels[panels.length - 1]);
    if (panels.length > 1) darkenColor(panels[0], leafColor);
    const pathbars = document.querySelectorAll(".treemap > .pathbar > .surface");
    for (const pathbar of pathbars) darkenColor(pathbar, leafColor);
  } catch (error) {
    console.warn("Failed to darken the treemap pathbar", error);
  }
}

// Element.computedStyleMap は Firefox に無いので、どのブラウザにもある getComputedStyle を使う。
// どちらも "rgb(r, g, b)" の形の文字列を返す
function getColor(elem: Element) {
  return window.getComputedStyle(elem).fill || "";
}

function darkenColor(elem: Element, originalColor: string) {
  if (getColor(elem) !== originalColor) return;
  const darkenedColor = originalColor.replace(
    /rgb\((\d+), (\d+), (\d+)\)/,
    (match, r, g, b) => `rgb(${dark(r)}, ${dark(g)}, ${dark(b)})`,
  );
  const newStyle = elem.attributes.getNamedItem("style")?.value.replace(originalColor, darkenedColor) || "";
  elem.setAttribute("style", newStyle);
}

function dark(rgb: string) {
  return Math.max(0, Number.parseInt(rgb) - 30);
}
