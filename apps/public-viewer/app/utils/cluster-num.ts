import type { Result } from "@/type";

export function getClusterNum(result: Result): Record<number, number> {
  const array = result.clusters.map((c) => c.level);
  return array.reduce(
    (acc, num) => {
      acc[num] = (acc[num] || 0) + 1;
      return acc;
    },
    {} as Record<number, number>,
  );
}
