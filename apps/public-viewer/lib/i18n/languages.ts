/**
 * 表示言語の定義と、選択した言語の保存・復元。
 *
 * 言語は URL のクエリ `?lang=` と localStorage の両方に保存する。
 * URL は共有リンクで言語を伝えるため、localStorage は同じブラウザで
 * 次のレポートを開いたときに引き継ぐため。shell 配布物（静的 HTML）でも
 * ブラウザだけで完結するよう、サーバーには依存しない。
 */

export const SUPPORTED_LANGUAGES = ["ja", "en", "ko"] as const;
export type Language = (typeof SUPPORTED_LANGUAGES)[number];
export const DEFAULT_LANGUAGE: Language = "ja";

/** 言語切替ボタンに表示する自己名称 */
export const LANGUAGE_LABELS: Record<Language, string> = {
  ja: "日本語",
  en: "English",
  ko: "한국어",
};

export const LANGUAGE_QUERY_KEY = "lang";
export const LANGUAGE_STORAGE_KEY = "kouchou-ai.language";

export function isLanguage(value: unknown): value is Language {
  return typeof value === "string" && (SUPPORTED_LANGUAGES as readonly string[]).includes(value);
}

/** `en-US` や `EN` のような表記も対応言語へ寄せる。対応外は undefined。 */
export function normalizeLanguage(value: unknown): Language | undefined {
  if (typeof value !== "string") return undefined;
  const base = value.trim().toLowerCase().split(/[-_]/)[0];
  return isLanguage(base) ? base : undefined;
}

type StorageLike = Pick<Storage, "getItem" | "setItem">;

/**
 * 初期表示の言語を決める。URL のクエリを最優先し、なければ保存済みの選択、
 * どちらもなければ既定（日本語）。
 */
export function resolveInitialLanguage(search: string, storage: StorageLike | null | undefined): Language {
  const fromQuery = normalizeLanguage(new URLSearchParams(search).get(LANGUAGE_QUERY_KEY));
  if (fromQuery) return fromQuery;
  try {
    const stored = normalizeLanguage(storage?.getItem(LANGUAGE_STORAGE_KEY));
    if (stored) return stored;
  } catch {
    // プライベートモード等で localStorage が使えない場合は既定に戻す
  }
  return DEFAULT_LANGUAGE;
}

/** 現在の URL に言語クエリを反映した `search` 文字列を返す（既定言語ではクエリを外す）。 */
export function withLanguageQuery(search: string, language: Language): string {
  const params = new URLSearchParams(search);
  if (language === DEFAULT_LANGUAGE) params.delete(LANGUAGE_QUERY_KEY);
  else params.set(LANGUAGE_QUERY_KEY, language);
  const next = params.toString();
  return next ? `?${next}` : "";
}

/**
 * `window.localStorage` を安全に取り出す。サンドボックスの iframe やサイトデータを拒否した設定では、
 * プロパティを読んだだけで SecurityError になるので、そのときは null を返す。
 */
export function getBrowserStorage(): StorageLike | null {
  try {
    return typeof window === "undefined" ? null : window.localStorage;
  } catch {
    return null;
  }
}

export function persistLanguage(language: Language, storage: StorageLike | null | undefined): void {
  try {
    storage?.setItem(LANGUAGE_STORAGE_KEY, language);
  } catch {
    // 保存できなくても表示は切り替わるので無視する
  }
}
