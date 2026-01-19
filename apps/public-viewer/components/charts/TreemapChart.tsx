import type { Argument, Cluster } from "@/type";
import type { PlotData } from "plotly.js";
import { ChartCore } from "./ChartCore";

type Props = {
  clusterList: Cluster[];
  argumentList: Argument[];
  onHover?: () => void;
  level: string;
  onTreeZoom: (level: string) => void;
  filteredArgumentIds?: string[]; // 追加: フィルター済みID
};

export function TreemapChart({ clusterList, argumentList, onHover, level, onTreeZoom, filteredArgumentIds }: Props) {
  // フィルタリングが有効かどうかをチェック
  const isFilteringActive = !!filteredArgumentIds;

  // フィルターされていない場合は全ての引数を表示
  const convertedArgumentList = argumentList.map((arg) => {
    const converted = convertArgumentToCluster(arg);

    // フィルターが適用されていて、フィルター結果に含まれない場合はグレーにする
    if (filteredArgumentIds && !filteredArgumentIds.includes(arg.arg_id)) {
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
    if (isFilteringActive && !filteredArgumentIds.includes(arg.arg_id)) {
      continue;
    }

    // 各クラスタIDに対して件数を増やす
    for (const clusterId of arg.cluster_ids) {
      if (clusterCounts[clusterId] !== undefined) {
        clusterCounts[clusterId]++;
      }
    }
  }

  const list = [{ ...clusterList[0], parent: "" }, ...clusterList.slice(1), ...convertedArgumentList];
  const ids = list.map((node) => node.id);
  const labels = list.map((node) => {
    return node.id === level ? node.label.replace(/(.{50})/g, "$1<br />") : node.label.replace(/(.{15})/g, "$1<br />");
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
    let takeaway = node.takeaway.replace(/(.{15})/g, "$1<br />");

    // クラスターノードの場合、フィルター情報を追加
    if (clusterCounts[node.id] !== undefined && isFilteringActive) {
      const originalCount = node.value;
      const filteredCount = clusterCounts[node.id];

      if (filteredCount < originalCount) {
        takeaway = `${takeaway}<br><br>元の件数: ${originalCount}<br>フィルター後: ${filteredCount}`;
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

  const data: Partial<PlotData & { maxdepth: number; pathbar: { thickness: number } }> = {
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
      opacity: list.map((node) => {
        // @ts-ignore filtered プロパティを追加したので無視
        return node.filtered ? 0.5 : 1; // フィルターに該当しないものは半透明に
      }),
    },
    // フィルター対象外のノードではホバー表示を無効にする
    hoverinfo: "text",
    hovertemplate: "%{customdata}<extra></extra>",
    hoverlabel: {
      align: "left",
    },
    texttemplate: isFilteringActive
      ? "%{label}<br>%{value:,}件 (フィルター後)<br>%{percentEntry:.2%}"
      : "%{label}<br>%{value:,}件<br>%{percentEntry:.2%}",
    maxdepth: 2,
    pathbar: {
      thickness: 28,
    },
  };

  const layout = {
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

  return (
    <ChartCore
      data={[data]}
      layout={layout}
      useResizeHandler={true}
      style={{ width: "100%", height: "100%" }}
      config={{
        responsive: true,
        displayModeBar: false,
        locale: "ja",
      }}
      onUpdate={darkenPathbar}
      onUnhover={darkenPathbar}
      onHover={() => {
        onHover ? onHover() : null;
        darkenPathbar();
      }}
      onClick={(event) => {
        const clickedNode = event.points[0];
        const newLevel = clickedNode.data.ids[clickedNode.pointNumber]?.toString() || "0";
        onTreeZoom(newLevel);
        // 元々のクリックイベントはキャンセルされるので無限ループにはならない
      }}
    />
  );
}

function convertArgumentToCluster(argument: Argument): Cluster {
  return {
    level: 3,
    id: argument.arg_id,
    label: argument.argument,
    takeaway: "",
    value: 1,
    parent: argument.cluster_ids[2],
    density_rank_percentile: 0,
  };
}

function darkenPathbar() {
  const panels = document.querySelectorAll(".treemap > .slice > .surface");
  const leafColor = getColor(panels[panels.length - 1]);
  if (panels.length > 1) darkenColor(panels[0], leafColor);
  const pathbars = document.querySelectorAll(".treemap > .pathbar > .surface");
  for (const pathbar of pathbars) darkenColor(pathbar, leafColor);
}

function getColor(elem: Element) {
  return elem.computedStyleMap().get("fill")?.toString() || "";
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
