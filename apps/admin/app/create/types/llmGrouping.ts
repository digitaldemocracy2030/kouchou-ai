// analysis-core の llm_grouping_specs.json と同じ既定値。
export const DEFAULT_LLM_GROUPING = {
  discovery_sample_size: 80,
  assignment_batch_size: 25,
  use_all_arguments: false,
};

export type LLMGroupingSettings = typeof DEFAULT_LLM_GROUPING;

export type LLMGroupingOptions = {
  [Key in keyof LLMGroupingSettings]?: LLMGroupingSettings[Key] | null;
};

export const isValidGroupingSize = (size: number) => Number.isSafeInteger(size) && size >= 1;

export function isValidLLMGrouping(settings: LLMGroupingSettings) {
  return (
    settings.use_all_arguments ||
    (isValidGroupingSize(settings.discovery_sample_size) && isValidGroupingSize(settings.assignment_batch_size))
  );
}

export function toLLMGroupingOptions(settings: LLMGroupingSettings): LLMGroupingOptions {
  return settings.use_all_arguments ? { use_all_arguments: true } : settings;
}
