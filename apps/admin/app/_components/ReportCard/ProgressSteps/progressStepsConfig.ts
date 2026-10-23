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

// 失敗した status の current_step が、今回実行する工程（steps）に無いときは、全工程を終えた後の失敗とみなす。
// analysis-core は実行しない工程（Web 経路の可視化など）でも current_job を書き換えるので、完了後に API 側で
// 失敗すると（成果物のアップロード失敗など）、current_step は実行していない工程名のまま error になる
export function isFailureAfterPlannedSteps(
  plannedSteps: string[] | null,
  currentStep: string | null,
  isError: boolean,
): boolean {
  return (
    isError &&
    currentStep !== null &&
    plannedSteps !== null &&
    plannedSteps.length > 0 &&
    !plannedSteps.includes(currentStep)
  );
}

export function resolveDisplaySteps(
  plannedSteps: string[] | null,
  currentStep: string | null,
  isError = false,
): DisplayStep[] {
  const keys = plannedSteps && plannedSteps.length > 0 ? [...plannedSteps] : [...defaultStepKeys];
  // 知らない工程名を足すのは、実行中と、steps の無い古い status のときだけ。
  // 全工程の後の失敗で足すと、実行していない工程に失敗マークが付く
  if (currentStep && !keys.includes(currentStep) && !isFailureAfterPlannedSteps(plannedSteps, currentStep, isError)) {
    keys.push(currentStep);
  }
  return keys.map((key) => ({ key, title: stepTitle(key) }));
}
