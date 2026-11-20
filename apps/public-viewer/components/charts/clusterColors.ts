import type { Cluster } from "@/type";

// 意見グループの配色のパレット。散布図（全体図）とツリーマップ（階層図）で同じ色を使い、
// 図を切り替えても同じ意見グループを色で追えるようにする（#337）。
// 参照を安定させて useMemo を効かせるため、モジュールスコープの定数として保持する。
export const CLUSTER_COLORS: readonly string[] = [
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

/** 並び順 index 番目の意見グループの色。パレットの数を超えたら先頭から繰り返す */
export function clusterColor(index: number): string {
  return CLUSTER_COLORS[index % CLUSTER_COLORS.length];
}

/**
 * 意見グループ id → 色の対応を作る。色は渡された配列の並び順で決まるので、
 * 同じ階層のクラスタを同じ順で渡せば、どの図でも同じ色になる。
 */
export function buildClusterColorMap(clusters: readonly Cluster[]): Record<string, string> {
  const map: Record<string, string> = {};
  clusters.forEach((cluster, index) => {
    map[cluster.id] = clusterColor(index);
  });
  return map;
}
