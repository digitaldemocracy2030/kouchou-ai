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

// 組み込み入力タイプ
export type BuiltinInputType = "file" | "spreadsheet";

// プラグインによる入力タイプ（plugin:{pluginId} 形式）
export type PluginInputType = `plugin:${string}`;

// 全入力タイプ
export type InputType = BuiltinInputType | PluginInputType;

// プラグインの状態
export interface PluginState {
  id: string;
  url: string;
  imported: boolean;
  loading: boolean;
  data: SpreadsheetComment[]; // SpreadsheetCommentと同じ形式を使用
  commentCount: number;
}
