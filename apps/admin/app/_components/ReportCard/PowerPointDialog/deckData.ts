import type { Result } from "@/type";

type DeckSource = Pick<Result, "overview"> & {
  comment_num?: number;
  config?: Pick<Result["config"], "name" | "question">;
  arguments: Pick<Result["arguments"][number], "argument" | "cluster_ids">[];
  clusters: Pick<Result["clusters"][number], "level" | "id" | "label" | "takeaway">[];
};

export function getDeckData(result: DeckSource) {
  const topics = result.clusters.filter((cluster) => cluster.level === 1);
  const topicIds = new Set(topics.map((topic) => topic.id));
  const opinionsByTopic = new Map<string, { count: number; examples: string[] }>();
  for (const opinion of result.arguments) {
    for (const id of new Set(opinion.cluster_ids)) {
      if (!topicIds.has(id)) continue;
      const entry = opinionsByTopic.get(id) ?? { count: 0, examples: [] };
      entry.count++;
      const text = opinion.argument.trim();
      if (text && entry.examples.length < 3 && !entry.examples.includes(text)) entry.examples.push(text);
      opinionsByTopic.set(id, entry);
    }
  }

  return {
    // config.name は入力データの識別名で、管理画面で入力したタイトルは config.question に入る
    title: result.config?.question || result.config?.name || "広聴AIレポート",
    question: result.config?.question || "",
    overview: result.overview || "",
    inputCount:
      Number.isSafeInteger(result.comment_num) && (result.comment_num ?? -1) >= 0 ? result.comment_num : undefined,
    opinionCount: result.arguments.length,
    topics: topics.map(({ id, label, takeaway }) => ({
      id,
      label,
      takeaway,
      ...(opinionsByTopic.get(id) ?? { count: 0, examples: [] }),
    })),
  };
}

export type DeckData = ReturnType<typeof getDeckData>;
