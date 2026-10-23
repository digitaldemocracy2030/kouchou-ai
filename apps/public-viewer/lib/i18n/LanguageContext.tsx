"use client";

import type { Result } from "@/type";
import { type ReactNode, createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import {
  DEFAULT_LANGUAGE,
  type Language,
  SUPPORTED_LANGUAGES,
  persistLanguage,
  resolveInitialLanguage,
  withLanguageQuery,
} from "./languages";
import { type Messages, getMessages } from "./messages";
import { localizeResult } from "./translateResult";

type LanguageContextValue = {
  language: Language;
  setLanguage: (language: Language) => void;
  messages: Messages;
};

/**
 * Provider の外（テストや開発用カタログ）でも日本語で動くよう、既定値を持たせる。
 * 切替は Provider がある場合だけ効く。
 */
const LanguageContext = createContext<LanguageContextValue>({
  language: DEFAULT_LANGUAGE,
  setLanguage: () => {},
  messages: getMessages(DEFAULT_LANGUAGE),
});

export function LanguageProvider({ children }: { children: ReactNode }) {
  // SSR と最初の描画は既定言語で行い、ブラウザで URL / localStorage を読んでから切り替える
  const [language, setLanguageState] = useState<Language>(DEFAULT_LANGUAGE);

  useEffect(() => {
    setLanguageState(resolveInitialLanguage(window.location.search, window.localStorage));
  }, []);

  useEffect(() => {
    document.documentElement.lang = getMessages(language).htmlLang;
  }, [language]);

  const setLanguage = useCallback((next: Language) => {
    if (!SUPPORTED_LANGUAGES.includes(next)) return;
    setLanguageState(next);
    persistLanguage(next, window.localStorage);
    const search = withLanguageQuery(window.location.search, next);
    window.history.replaceState(
      window.history.state,
      "",
      `${window.location.pathname}${search}${window.location.hash}`,
    );
  }, []);

  const value = useMemo(() => ({ language, setLanguage, messages: getMessages(language) }), [language, setLanguage]);

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
}

export function useLanguage(): LanguageContextValue {
  return useContext(LanguageContext);
}

export function useMessages(): Messages {
  return useContext(LanguageContext).messages;
}

/** 表示言語の翻訳を適用した Result。翻訳が無ければ元の参照をそのまま返す。 */
export function useLocalizedResult(result: Result): Result {
  const { language } = useLanguage();
  return useMemo(() => localizeResult(result, language), [result, language]);
}
