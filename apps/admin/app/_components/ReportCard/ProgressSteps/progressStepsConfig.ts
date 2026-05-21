export const steps = [
  { key: "extraction", title: "抽出" },
  { key: "embedding", title: "埋め込み" },
  { key: "hierarchical_clustering", title: "意見グループ化" },
  { key: "hierarchical_initial_labelling", title: "初期ラベリング" },
  { key: "hierarchical_merge_labelling", title: "統合ラベリング" },
  { key: "hierarchical_overview", title: "概要生成" },
  { key: "hierarchical_aggregation", title: "集約" },
  { key: "hierarchical_visualization", title: "可視化" },
] as const;

export const stepKeys = steps.map(({ key }) => key);
