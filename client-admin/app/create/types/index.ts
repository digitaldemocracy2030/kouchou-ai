// 型定義
export interface SpreadsheetComment {
  id?: string;
  comment: string;
  source?: string | null;
  url?: string | null;
}

export interface ClusterSettings {
  lv1: number;
  lv2: number;
}

export interface PromptSettings {
  extraction: string;
  initial_labelling: string;
  merge_labelling: string;
  overview: string;
}

export type InputType = "file" | "spreadsheet";
