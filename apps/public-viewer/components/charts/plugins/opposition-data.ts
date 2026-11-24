import type { OppositionAxis, Result } from "@/type";

export const OPPOSITION_CHART = "opposition";

export function getOppositionAxes(result: Result): OppositionAxis[] {
  if (!Array.isArray(result.opposition_axes)) return [];
  const clusters = new Set(result.clusters.filter((cluster) => cluster.level > 0).map((cluster) => cluster.id));
  const seen = new Set<string>();
  return result.opposition_axes.filter((axis) => {
    if (
      !axis ||
      typeof axis.id !== "string" ||
      !axis.id ||
      seen.has(axis.id) ||
      !clusters.has(axis.cluster_id) ||
      typeof axis.name !== "string" ||
      typeof axis.left_pole !== "string" ||
      typeof axis.right_pole !== "string" ||
      !axis.scores ||
      typeof axis.scores !== "object" ||
      Array.isArray(axis.scores)
    ) {
      return false;
    }
    seen.add(axis.id);
    return true;
  });
}
