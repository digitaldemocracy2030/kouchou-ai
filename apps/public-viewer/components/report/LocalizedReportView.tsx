"use client";

import { Analysis } from "@/components/report/Analysis";
import { BackButton } from "@/components/report/BackButton";
import { ClientContainer } from "@/components/report/ClientContainer";
import { LanguageToggle } from "@/components/report/LanguageToggle";
import { Overview } from "@/components/report/Overview";
import { ReadingGuide } from "@/components/report/ReadingGuide";
import { useLanguage, useLocalizedResult } from "@/lib/i18n/LanguageContext";
import { DEFAULT_LANGUAGE } from "@/lib/i18n/languages";
import { hasReportTranslation } from "@/lib/i18n/translateResult";
import type { Result } from "@/type";
import { Box, Flex, Separator, Text } from "@chakra-ui/react";
import type { ReactNode } from "react";

/**
 * レポート本文。表示言語に応じて `translations` を適用した Result を
 * 下のコンポーネントへ渡す。翻訳が無い言語では元の言語のまま表示し、その旨を添える。
 */
export function LocalizedReportView({ result, reporter }: { result: Result; reporter: ReactNode }) {
  const { language, messages } = useLanguage();
  const localized = useLocalizedResult(result);
  const showUntranslatedNote = language !== DEFAULT_LANGUAGE && !hasReportTranslation(result, language);

  return (
    <Box className="container" mt="8">
      <Flex maxW={"750px"} mx={"auto"} mb={4} justifyContent={"flex-end"} alignItems={"center"} gap={3} flexWrap="wrap">
        <LanguageToggle />
      </Flex>
      {showUntranslatedNote && (
        <Text maxW={"750px"} mx={"auto"} mb={4} fontSize={"sm"} color={"gray.600"} role="note">
          {messages.reportNotTranslated}
        </Text>
      )}
      <Overview result={localized} />
      <ReadingGuide />
      <ClientContainer result={localized} />
      <Analysis result={localized} />
      <BackButton />
      <Separator my={12} maxW={"750px"} mx={"auto"} />
      <Box maxW={"750px"} mx={"auto"} mb={24}>
        {reporter}
      </Box>
    </Box>
  );
}
