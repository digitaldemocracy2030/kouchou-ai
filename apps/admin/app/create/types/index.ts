// 型定義
export interface SpreadsheetComment {
  id?: string;
  comment: string;
  source?: string | null;
  url?: string | null;
  [key: string]: string | null | undefined;
}

export interface ClusterSettings {
  lv1: number;
  lv2: number;
}

export interface PromptSettings {
  extraction: string;
  initialLabelling: string;
  mergeLabelling: string;
  overview: string;
}

export type InputType = "file" | "spreadsheet";
