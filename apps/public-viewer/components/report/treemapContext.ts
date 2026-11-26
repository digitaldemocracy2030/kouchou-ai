import { toIdSet } from "@/lib/argumentIndex";
import type { Cluster, Result } from "@/type";

type Group = { id: string; parent: string; label: string; takeaway: string; value: number };
type Opinion = { arg_id: string; argument: string; cluster_ids: string[] };

export function applyTreemapDensityFilter(
  result: Result,
  densityFilteredClusters: Cluster[],
  filteredIds: string[] | undefined,
): Result {
  const root = result.clusters[0];
  const densityIds = new Set(densityFilteredClusters.map((cluster) => cluster.id));
  const attributeIds = toIdSet(filteredIds);
  const visibleClusterIds = new Set<string>();
  const arguments_ = result.arguments.filter((opinion) => {
    if (attributeIds && !attributeIds.has(opinion.arg_id)) return false;
    if (!opinion.cluster_ids.every((id) => densityIds.has(id))) return false;
    for (const id of opinion.cluster_ids) visibleClusterIds.add(id);
    return true;
  });
  return {
    ...result,
    arguments: arguments_,
    // 表示する意見がない枝は図と説明欄から除き、全体へ戻るためのルートは残す。
    clusters: result.clusters.filter((cluster) => cluster === root || visibleClusterIds.has(cluster.id)),
    // 密度だけで絞った場合も、上位階層の件数と割合を絞り込み後の値にする。
    filteredArgumentIds: arguments_.map((opinion) => opinion.arg_id),
  };
}

export function resolveFilteredTreemapLevel(level: string, source: Result, filtered: Result): string {
  const visibleIds = new Set(filtered.clusters.map((cluster) => cluster.id));
  if (!level || visibleIds.has(level) || filtered.filteredArgumentIds?.includes(level)) return level;

  const parents = new Map(source.clusters.map((cluster) => [cluster.id, cluster.parent]));
  let parent = parents.get(level) ?? source.arguments.find((opinion) => opinion.arg_id === level)?.cluster_ids.at(-1);
  for (let depth = 0; parent && depth < parents.size; depth++) {
    if (visibleIds.has(parent)) return parent;
    parent = parents.get(parent);
  }
  return filtered.clusters[0]?.id ?? level;
}

// Keep this navigation/count contract aligned with the other viewer.
export function treemapContext(
  clusters: Group[],
  arguments_: Opinion[],
  level: string,
  filteredIds?: Iterable<string> | null,
) {
  const root = clusters[0];
  const allowed = filteredIds == null ? null : new Set(filteredIds);
  const counts = new Map<string, number>();
  let total = 0;
  for (const arg of arguments_) {
    if (allowed && !allowed.has(arg.arg_id)) continue;
    total++;
    for (const id of arg.cluster_ids) counts.set(id, (counts.get(id) ?? 0) + 1);
  }
  const opinion = arguments_.find((arg) => arg.arg_id === level);
  const current =
    clusters.find((cluster) => cluster.id === level) ??
    (opinion
      ? {
          id: opinion.arg_id,
          parent: opinion.cluster_ids[opinion.cluster_ids.length - 1],
          label: opinion.argument,
          takeaway: "",
          value: 1,
        }
      : root);
  const count = (group: Group) =>
    allowed
      ? group.id === opinion?.arg_id
        ? Number(allowed.has(group.id))
        : (counts.get(group.id) ?? 0)
      : group.value;
  const denominator = allowed ? total : (root?.value ?? arguments_.length);
  const describe = (group: Group) => ({
    ...group,
    count: count(group),
    percentage: denominator > 0 ? `${((100 * count(group)) / denominator).toFixed(2)}%` : "—",
  });
  return {
    root,
    current: current && describe(current),
    parent: current && current.id !== root?.id ? clusters.find((group) => group.id === current.parent) : undefined,
    children: clusters
      .filter((group) => group.id !== current?.id && group.parent === current?.id)
      .map(describe)
      .sort((a, b) => b.count - a.count),
    isOpinion: !!opinion,
    filtering: allowed !== null,
  };
}
