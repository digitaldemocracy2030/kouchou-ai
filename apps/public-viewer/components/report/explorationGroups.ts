import type { Argument } from "@/type";

export const MAX_GROUPS = 12;
export const DEFAULT_EXPLORATION = { count: 4, stance: 0, topic: 0, reason: 0, topicKey: "", reasonKey: "" };
export type ExplorationSettings = typeof DEFAULT_EXPLORATION;

const queryKeys = {
  count: "groups",
  stance: "stance",
  topic: "topicWeight",
  reason: "reasonWeight",
  topicKey: "topicField",
  reasonKey: "reasonField",
} as const;

function boundedInteger(value: string | null, min: number, max: number, fallback: number) {
  if (!value || !/^\d+$/.test(value)) return fallback;
  return Math.max(min, Math.min(max, Number(value)));
}

export function readExploration(search: string): ExplorationSettings | undefined {
  const params = new URLSearchParams(search);
  if (params.get("explore") !== "1") return;
  return {
    count: boundedInteger(params.get(queryKeys.count), 2, MAX_GROUPS, DEFAULT_EXPLORATION.count),
    stance: boundedInteger(params.get(queryKeys.stance), 0, 10, 0),
    topic: boundedInteger(params.get(queryKeys.topic), 0, 10, 0),
    reason: boundedInteger(params.get(queryKeys.reason), 0, 10, 0),
    topicKey: params.get(queryKeys.topicKey) ?? "",
    reasonKey: params.get(queryKeys.reasonKey) ?? "",
  };
}

export function explorationUrl(current: string, settings: ExplorationSettings) {
  const url = new URL(current);
  url.searchParams.set("explore", "1");
  for (const key of Object.keys(queryKeys) as (keyof ExplorationSettings)[]) {
    if (settings[key]) url.searchParams.set(queryKeys[key], String(settings[key]));
    else url.searchParams.delete(queryKeys[key]);
  }
  url.hash = "report-exploration";
  return url;
}

export function coordinateOpinions(opinions: Argument[]) {
  return opinions.filter((opinion) => Number.isFinite(opinion.x) && Number.isFinite(opinion.y));
}

export function opinionStance(opinion: Argument) {
  const value = opinion.attributes?.stance_score;
  return typeof value === "number" && value >= -1 && value <= 1 ? value : undefined;
}

function category(opinion: Argument, key: string) {
  const value = key && Object.hasOwn(opinion.attributes ?? {}, key) ? opinion.attributes?.[key] : undefined;
  return typeof value === "string" && value.trim() ? value : undefined;
}

export function categoryKeys(opinions: Argument[]) {
  const keys = new Set<string>();
  for (const opinion of opinions) {
    for (const [key, value] of Object.entries(opinion.attributes ?? {})) {
      if (typeof value === "string" && value.trim()) keys.add(key);
    }
  }
  return [...keys].sort();
}

const DEFAULT_FIELD_WEIGHT = 5;

// 属性を初めて選んだときだけ既定の重みを入れる。選択中の属性を切り替えるときは、0 を含めて今の重みを保つ
export function fieldWeightAfterSelect(currentKey: string, nextKey: string, currentWeight: number) {
  if (!nextKey) return 0;
  return currentKey ? currentWeight : DEFAULT_FIELD_WEIGHT;
}

export function explorationSettings(settings: ExplorationSettings, opinions: Argument[], keys: string[]) {
  const topicKey = keys.includes(settings.topicKey) ? settings.topicKey : "";
  const reasonKey = keys.includes(settings.reasonKey) ? settings.reasonKey : "";
  return {
    count: Math.min(opinions.length, settings.count),
    stance: opinions.some((opinion) => opinionStance(opinion) !== undefined) ? settings.stance : 0,
    topic: topicKey ? settings.topic : 0,
    reason: reasonKey ? settings.reason : 0,
    topicKey,
    reasonKey,
  };
}

function normalizeCoordinates(opinions: Argument[], key: "x" | "y") {
  let min = Number.POSITIVE_INFINITY;
  let max = Number.NEGATIVE_INFINITY;
  for (const opinion of opinions) {
    min = Math.min(min, opinion[key]);
    max = Math.max(max, opinion[key]);
  }
  const range = max - min;
  if (range === 0) return () => 0;
  if (Number.isFinite(range)) return (opinion: Argument) => (opinion[key] - min) / range;
  return (opinion: Argument) => (opinion[key] / 2 - min / 2) / (max / 2 - min / 2);
}

type Dimension =
  | { weight: number; kind: "number"; value: (opinion: Argument) => number | undefined }
  | { weight: number; kind: "category"; value: (opinion: Argument) => string | undefined };

type Split = { score: number; partition: (opinion: Argument) => boolean | undefined };

function numericSplit(group: Argument[], dimension: Extract<Dimension, { kind: "number" }>): Split | undefined {
  const values = group.flatMap((opinion) => {
    const value = dimension.value(opinion);
    return value === undefined ? [] : [value];
  });
  if (values.length < 2) return;
  values.sort((a, b) => a - b);
  if (values[0] === values.at(-1)) return;

  // Use the boundary closest to the median. Equal values always stay in the same half.
  const middle = values.length / 2;
  let boundary = 1;
  let distance = Number.POSITIVE_INFINITY;
  for (let index = 1; index < values.length; index++) {
    if (values[index - 1] !== values[index] && Math.abs(index - middle) < distance) {
      boundary = index;
      distance = Math.abs(index - middle);
    }
  }
  const mean = values.reduce((sum, value) => sum + value, 0) / values.length;
  const variation = values.reduce((sum, value) => sum + (value - mean) ** 2, 0);
  return {
    score: variation * 4 * dimension.weight,
    partition: (opinion) => {
      const value = dimension.value(opinion);
      return value === undefined ? undefined : value < values[boundary];
    },
  };
}

function categoricalSplit(group: Argument[], dimension: Extract<Dimension, { kind: "category" }>): Split | undefined {
  const counts = new Map<string, number>();
  let known = 0;
  for (const opinion of group) {
    const value = dimension.value(opinion);
    if (value === undefined) continue;
    counts.set(value, (counts.get(value) ?? 0) + 1);
    known++;
  }
  if (counts.size < 2) return;
  const ordered = [...counts].sort(([a, aCount], [b, bCount]) => bCount - aCount || (a < b ? -1 : 1));
  const left = new Set<string>();
  let leftCount = 0;
  let rightCount = 0;
  for (const [value, count] of ordered) {
    if (leftCount <= rightCount) {
      left.add(value);
      leftCount += count;
    } else {
      rightCount += count;
    }
  }
  const concentration = ordered.reduce((sum, [, count]) => sum + (count / known) ** 2, 0);
  return {
    score: known * (1 - concentration) * dimension.weight,
    partition: (opinion) => {
      const value = dimension.value(opinion);
      return value === undefined ? undefined : left.has(value);
    },
  };
}

function splitGroup(opinions: Argument[], split: Split): [Argument[], Argument[]] {
  const left: Argument[] = [];
  const right: Argument[] = [];
  const unknown: Argument[] = [];
  for (const opinion of opinions) {
    const side = split.partition(opinion);
    (side === undefined ? unknown : side ? left : right).push(opinion);
  }
  for (const opinion of unknown) (left.length <= right.length ? left : right).push(opinion);
  return [left, right];
}

export function exploreGroups(opinions: Argument[], settings: ExplorationSettings): Argument[][] {
  if (!opinions.length) return [];
  const dimensions: Dimension[] = [
    { weight: 1, kind: "number", value: normalizeCoordinates(opinions, "x") },
    { weight: 1, kind: "number", value: normalizeCoordinates(opinions, "y") },
    {
      weight: settings.stance / 2,
      kind: "number",
      value: (opinion) => {
        const value = opinionStance(opinion);
        return value === undefined ? undefined : (value + 1) / 2;
      },
    },
    { weight: settings.topic / 2, kind: "category", value: (opinion) => category(opinion, settings.topicKey) },
    { weight: settings.reason / 2, kind: "category", value: (opinion) => category(opinion, settings.reasonKey) },
  ];

  function groupWithSplit(group: Argument[]) {
    let best: Split | undefined;
    for (const dimension of dimensions) {
      if (dimension.weight <= 0) continue;
      const split = dimension.kind === "number" ? numericSplit(group, dimension) : categoricalSplit(group, dimension);
      if (split && (!best || split.score > best.score)) best = split;
    }
    return { opinions: group, split: best };
  }

  const groups = [groupWithSplit(opinions)];
  while (groups.length < settings.count) {
    const next = groups.reduce((best, group, index) => {
      return (group.split?.score ?? 0) > (groups[best]?.split?.score ?? 0) ? index : best;
    }, 0);
    const group = groups[next];
    if (!group.split) break;
    const [left, right] = splitGroup(group.opinions, group.split);
    groups.splice(next, 1, groupWithSplit(left), groupWithSplit(right));
  }
  return groups.map((group) => group.opinions);
}
