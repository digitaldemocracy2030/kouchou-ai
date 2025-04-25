import { useState } from "react";
import { extractionPrompt } from "../extractionPrompt";
import { initialLabellingPrompt } from "../initialLabellingPrompt";
import { mergeLabellingPrompt } from "../mergeLabellingPrompt";
import { overviewPrompt } from "../overviewPrompt";

// カスタムフック: プロンプト設定の管理
export function usePromptSettings() {
  const [extraction, setExtraction] = useState<string>(extractionPrompt);
  const [initial_labelling, setInitialLabelling] = useState<string>(initialLabellingPrompt);
  const [merge_labelling, setMergeLabelling] = useState<string>(mergeLabellingPrompt);
  const [overview, setOverview] = useState<string>(overviewPrompt);

  return {
    extraction,
    initial_labelling,
    merge_labelling,
    overview,
    setExtraction,
    setInitialLabelling,
    setMergeLabelling,
    setOverview,
    getPromptSettings: () => ({
      extraction,
      initial_labelling,
      merge_labelling,
      overview
    })
  };
}
