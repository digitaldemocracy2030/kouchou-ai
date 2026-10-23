// analysis-core の工程名と表示名。分析方式ごとの工程の並びは step-json の steps（plan のうち実行する工程）で受け取る
const stepTitles: Record<string, string> = {
  extraction: "抽出",
  opinion_classification: "意見分類",
  embedding: "埋め込み",
  hierarchical_clustering: "意見グループ化",
  llm_grouping: "LLM直接グルーピング",
  hierarchical_initial_labelling: "初期ラベリング",
  hierarchical_merge_labelling: "統合ラベリング",
  hierarchical_overview: "概要生成",
  hierarchical_aggregation: "集約",
  hierarchical_visualization: "可視化",
};

// steps を返さない（plan の無い古い status の）ときに使う既定の工程（階層クラスタリング）
export const defaultStepKeys = [
  "extraction",
  "embedding",
  "hierarchical_clustering",
  "hierarchical_initial_labelling",
  "hierarchical_merge_labelling",
  "hierarchical_overview",
  "hierarchical_aggregation",
  "hierarchical_visualization",
];

export type DisplayStep = { key: string; title: string };

// 知らない工程名（将来の分析方式やプラグイン）も捨てずに、工程名のまま表示する
export function stepTitle(key: string): string {
  return stepTitles[key] ?? key;
}

export function resolveDisplaySteps(plannedSteps: string[] | null, currentStep: string | null): DisplayStep[] {
  const keys = plannedSteps && plannedSteps.length > 0 ? [...plannedSteps] : [...defaultStepKeys];
  if (currentStep && !keys.includes(currentStep)) {
    keys.push(currentStep);
  }
  return keys.map((key) => ({ key, title: stepTitle(key) }));
}
