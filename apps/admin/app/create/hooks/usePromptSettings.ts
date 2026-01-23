import { useState } from "react";
import { extractionPrompt } from "../extractionPrompt";
import { initialLabellingPrompt } from "../initialLabellingPrompt";
import { mergeLabellingPrompt } from "../mergeLabellingPrompt";
import { overviewPrompt } from "../overviewPrompt";

// カスタムフック: プロンプト設定の管理
export function usePromptSettings() {
  const [extraction, setExtraction] = useState<string>(extractionPrompt);
  const [initialLabelling, setInitialLabelling] = useState<string>(initialLabellingPrompt);
  const [mergeLabelling, setMergeLabelling] = useState<string>(mergeLabellingPrompt);
  const [overview, setOverview] = useState<string>(overviewPrompt);

  return {
    extraction,
    initialLabelling,
    mergeLabelling,
    overview,
    setExtraction,
    setInitialLabelling,
    setMergeLabelling,
    setOverview,
    getPromptSettings: () => ({
      extraction,
      initialLabelling,
      mergeLabelling,
      overview,
    }),
  };
}
