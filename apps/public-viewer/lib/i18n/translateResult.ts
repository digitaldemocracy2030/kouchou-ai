/**
 * 分析結果に含まれる `translations` を使って、レポート本文を表示言語に差し替える。
 *
 * `translations` の形（analysis-core の translate CLI が生成する）:
 *
 * ```json
 * {
 *   "en": {
 *     "clusters": { "<cluster id>": { "label": "...", "takeaway": "..." } },
 *     "overview": "...",
 *     "question": "...",
 *     "intro": "...",
 *     "arguments": { "<arg_id>": "..." }
 *   }
 * }
 * ```
 *
 * どのキーも省略できる。見つからない文言は元の言語のまま表示する。
 * Talk to the City 由来の旧形式（言語ごとに「元の文字列 → 訳文」の辞書）も
 * 読めるようにしている。
 */

import type { Result } from "@/type";
import { normalizeLanguage } from "./languages";

export type ClusterTranslation = { label?: string; takeaway?: string };

export type ReportTranslation = {
  clusters?: Record<string, ClusterTranslation>;
  overview?: string;
  question?: string;
  intro?: string;
  arguments?: Record<string, string>;
  /** 旧形式: 元の文字列をキーにした訳文の辞書 */
  texts?: Record<string, string>;
};

const STRUCTURED_KEYS = ["clusters", "overview", "question", "intro", "arguments"] as const;

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function stringMap(value: unknown): Record<string, string> | undefined {
  if (!isRecord(value)) return undefined;
  const entries = Object.entries(value).filter((entry): entry is [string, string] => typeof entry[1] === "string");
  return entries.length > 0 ? Object.fromEntries(entries) : undefined;
}

function clusterMap(value: unknown): Record<string, ClusterTranslation> | undefined {
  if (!isRecord(value)) return undefined;
  const result: Record<string, ClusterTranslation> = {};
  for (const [id, raw] of Object.entries(value)) {
    if (!isRecord(raw)) continue;
    const entry: ClusterTranslation = {};
    if (typeof raw.label === "string" && raw.label) entry.label = raw.label;
    if (typeof raw.takeaway === "string") entry.takeaway = raw.takeaway;
    if (entry.label !== undefined || entry.takeaway !== undefined) result[id] = entry;
  }
  return Object.keys(result).length > 0 ? result : undefined;
}

/** 言語コードに対応する翻訳を取り出して正規化する。無ければ undefined。 */
export function getReportTranslation(translations: unknown, language: string): ReportTranslation | undefined {
  if (!isRecord(translations)) return undefined;
  const wanted = normalizeLanguage(language) ?? language;
  const key = Object.keys(translations).find((k) => k === language || normalizeLanguage(k) === wanted);
  if (key === undefined) return undefined;
  const raw = translations[key];
  if (!isRecord(raw)) return undefined;

  const structured = STRUCTURED_KEYS.some((k) => k in raw);
  if (!structured) {
    const texts = stringMap(raw);
    return texts ? { texts } : undefined;
  }

  const result: ReportTranslation = {};
  const clusters = clusterMap(raw.clusters);
  if (clusters) result.clusters = clusters;
  if (typeof raw.overview === "string" && raw.overview) result.overview = raw.overview;
  if (typeof raw.question === "string" && raw.question) result.question = raw.question;
  if (typeof raw.intro === "string" && raw.intro) result.intro = raw.intro;
  const args = stringMap(raw.arguments);
  if (args) result.arguments = args;
  return Object.keys(result).length > 0 ? result : undefined;
}

/** 表示言語の翻訳が結果に含まれているか（元の言語と同じ場合は false）。 */
export function hasReportTranslation(result: Pick<Result, "translations">, language: string): boolean {
  return getReportTranslation(result.translations, language) !== undefined;
}

/**
 * 翻訳を適用した Result を返す。翻訳が無い場合は同じオブジェクトをそのまま返すので、
 * 参照の同一性に依存する memo を壊さない。
 */
export function localizeResult(result: Result, language: string): Result {
  const t = getReportTranslation(result.translations, language);
  if (!t) return result;
  const texts = t.texts ?? {};

  let clustersChanged = false;
  const clusters = result.clusters.map((cluster) => {
    const entry = t.clusters?.[cluster.id];
    const label = entry?.label ?? texts[cluster.label] ?? cluster.label;
    const takeaway = entry?.takeaway ?? texts[cluster.takeaway] ?? cluster.takeaway;
    if (label === cluster.label && takeaway === cluster.takeaway) return cluster;
    clustersChanged = true;
    return { ...cluster, label, takeaway };
  });

  let argumentsChanged = false;
  const args =
    t.arguments || t.texts
      ? result.arguments.map((argument) => {
          const translated = t.arguments?.[argument.arg_id] ?? texts[argument.argument];
          if (!translated || translated === argument.argument) return argument;
          argumentsChanged = true;
          return { ...argument, argument: translated };
        })
      : result.arguments;

  const overview = t.overview ?? texts[result.overview] ?? result.overview;
  const question = t.question ?? texts[result.config.question] ?? result.config.question;
  const intro = t.intro ?? texts[result.config.intro] ?? result.config.intro;
  const configChanged = question !== result.config.question || intro !== result.config.intro;

  if (!clustersChanged && !argumentsChanged && overview === result.overview && !configChanged) return result;

  return {
    ...result,
    clusters: clustersChanged ? clusters : result.clusters,
    arguments: argumentsChanged ? args : result.arguments,
    overview,
    config: configChanged ? { ...result.config, question, intro } : result.config,
  };
}
