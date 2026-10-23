"use client";

import { useLanguage } from "@/lib/i18n/LanguageContext";
import { LANGUAGE_LABELS, SUPPORTED_LANGUAGES } from "@/lib/i18n/languages";
import { Button, HStack } from "@chakra-ui/react";

type Props = {
  /** 通常表示は md、全画面ツールバーなど狭い場所は sm */
  size?: "sm" | "md";
};

/**
 * 表示言語（日本語 / English / 한국어）の切替。
 *
 * 状態は LanguageProvider が持つので、レポート本文の上と全画面ツールバーの
 * どちらに置いても同じ選択を共有する。全画面ツールバーに他のボタンが並んでも
 * 収まるよう、依存は Chakra の Button だけにしている。
 */
export function LanguageToggle({ size = "md" }: Props) {
  const { language, setLanguage, messages } = useLanguage();
  const height = size === "sm" ? "36px" : "44px";
  return (
    <HStack
      as="fieldset"
      aria-label={messages.languageSwitcher}
      gap={0}
      border="none"
      p={0}
      m={0}
      minW={0}
      data-testid="language-toggle"
    >
      {SUPPORTED_LANGUAGES.map((lang, index) => {
        const selected = lang === language;
        return (
          <Button
            key={lang}
            type="button"
            lang={lang}
            aria-pressed={selected}
            onClick={() => setLanguage(lang)}
            variant={selected ? "solid" : "outline"}
            size={size}
            h={height}
            px={3}
            fontWeight={selected ? "bold" : "normal"}
            borderRadius={0}
            borderLeftRadius={index === 0 ? "md" : 0}
            borderRightRadius={index === SUPPORTED_LANGUAGES.length - 1 ? "md" : 0}
            ml={index === 0 ? 0 : "-1px"}
          >
            {LANGUAGE_LABELS[lang]}
          </Button>
        );
      })}
    </HStack>
  );
}
