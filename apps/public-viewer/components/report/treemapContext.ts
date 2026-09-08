type Group = { id: string; parent: string; label: string; takeaway: string; value: number };
type Opinion = { arg_id: string; argument: string; cluster_ids: string[] };

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
