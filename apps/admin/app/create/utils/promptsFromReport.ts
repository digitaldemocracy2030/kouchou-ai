import { extractionPrompt } from "../extractionPrompt";
import { initialLabellingPrompt } from "../initialLabellingPrompt";
import { mergeLabellingPrompt } from "../mergeLabellingPrompt";
import { overviewPrompt } from "../overviewPrompt";

/**
 * 既存のレポートを手本に、新規作成画面のプロンプトを読み込むためのロジック（#1203）。
 * 入力データや他の設定は読み込まず、各工程のプロンプトだけを扱う。
 */

export type PromptValues = {
  extraction: string;
  initialLabelling: string;
  mergeLabelling: string;
  overview: string;
};

export type PromptKey = keyof PromptValues;

export const PROMPT_KEYS: PromptKey[] = ["extraction", "initialLabelling", "mergeLabelling", "overview"];

export const PROMPT_LABELS: Record<PromptKey, string> = {
  extraction: "抽出",
  initialLabelling: "初期ラベリング",
  mergeLabelling: "統合ラベリング",
  overview: "要約",
};

export const DEFAULT_PROMPTS: PromptValues = {
  extraction: extractionPrompt,
  initialLabelling: initialLabellingPrompt,
  mergeLabelling: mergeLabellingPrompt,
  overview: overviewPrompt,
};

/** `/api/admin/reports/:slug/config` が返す config のうち、プロンプトに関わる部分 */
export type ReportPromptConfig = {
  analysis_mode?: string | null;
  extraction?: { prompt?: string | null } | null;
  hierarchical_initial_labelling?: { prompt?: string | null } | null;
  hierarchical_merge_labelling?: { prompt?: string | null } | null;
  hierarchical_overview?: { prompt?: string | null } | null;
};

const nonEmpty = (value: string | null | undefined): string | undefined =>
  typeof value === "string" && value.trim() !== "" ? value : undefined;

/**
 * config からプロンプトを取り出す。保存されていない工程（LLM 直接グルーピングで作った
 * レポートの初期・統合ラベリングなど）や空のプロンプトは含めない。
 */
export function promptsFromReportConfig(config: ReportPromptConfig | null | undefined): Partial<PromptValues> {
  const result: Partial<PromptValues> = {};
  const extraction = nonEmpty(config?.extraction?.prompt);
  const initialLabelling = nonEmpty(config?.hierarchical_initial_labelling?.prompt);
  const mergeLabelling = nonEmpty(config?.hierarchical_merge_labelling?.prompt);
  const overview = nonEmpty(config?.hierarchical_overview?.prompt);
  if (extraction !== undefined) result.extraction = extraction;
  if (initialLabelling !== undefined) result.initialLabelling = initialLabelling;
  if (mergeLabelling !== undefined) result.mergeLabelling = mergeLabelling;
  if (overview !== undefined) result.overview = overview;
  return result;
}

export type PromptLoadPlan = {
  /** 読み込み後のフォームの値 */
  next: PromptValues;
  /** 手本のレポートから読み込む工程 */
  loaded: PromptKey[];
  /** 手本のレポートに保存されておらず、今の内容のままにする工程 */
  missing: PromptKey[];
  /** 利用者が既定から変えた内容が、読み込みで置き換わる工程（確認が要る） */
  overwritten: PromptKey[];
};

/**
 * 今のフォームの値に、手本のレポートのプロンプトを当てた結果を求める。
 * 既定のままの工程や、読み込む内容と同じ工程は「上書き」に数えない。
 */
export function planPromptLoad(
  current: PromptValues,
  config: ReportPromptConfig | null | undefined,
  defaults: PromptValues = DEFAULT_PROMPTS,
): PromptLoadPlan {
  const fromReport = promptsFromReportConfig(config);
  const next: PromptValues = { ...current };
  const loaded: PromptKey[] = [];
  const missing: PromptKey[] = [];
  const overwritten: PromptKey[] = [];

  for (const key of PROMPT_KEYS) {
    const value = fromReport[key];
    if (value === undefined) {
      missing.push(key);
      continue;
    }
    loaded.push(key);
    next[key] = value;
    if (current[key] !== defaults[key] && current[key] !== value) {
      overwritten.push(key);
    }
  }

  return { next, loaded, missing, overwritten };
}

/** 読み込んだ工程のうち、その後に利用者が編集した工程 */
export function editedSinceLoad(current: PromptValues, loadedValues: PromptValues, loaded: PromptKey[]): PromptKey[] {
  return loaded.filter((key) => current[key] !== loadedValues[key]);
}

/** 「抽出・要約」のように工程名をつなぐ */
export function formatPromptKeys(keys: PromptKey[]): string {
  return keys.map((key) => PROMPT_LABELS[key]).join("・");
}

export type PromptSourceReport = {
  slug: string;
  title: string;
  createdAt?: string;
};

/** 選択肢に並べるため、新しいレポートを先に並べる（作成日時が無いものは最後） */
export function sortPromptSourceReports(reports: PromptSourceReport[]): PromptSourceReport[] {
  return [...reports].sort((a, b) => {
    const ta = a.createdAt ? Date.parse(a.createdAt) : Number.NaN;
    const tb = b.createdAt ? Date.parse(b.createdAt) : Number.NaN;
    const va = Number.isNaN(ta) ? Number.NEGATIVE_INFINITY : ta;
    const vb = Number.isNaN(tb) ? Number.NEGATIVE_INFINITY : tb;
    if (va !== vb) return vb - va;
    return a.slug.localeCompare(b.slug);
  });
}

/** 選択肢の表示名。タイトルが無いレポートは ID で示す */
export function promptSourceLabel(report: PromptSourceReport): string {
  const title = report.title?.trim();
  return title ? `${title}（${report.slug}）` : report.slug;
}
