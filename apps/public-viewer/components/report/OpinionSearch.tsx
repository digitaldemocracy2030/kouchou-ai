import { useMessages } from "@/lib/i18n/LanguageContext";
import { Box, Button, Flex, Input, Text } from "@chakra-ui/react";
import { useEffect, useId, useRef } from "react";

type Props = {
  query: string;
  matchCount: number;
  onSearch: (query: string) => void;
};

export function OpinionSearch({ query, matchCount, onSearch }: Props) {
  const messages = useMessages();
  const inputId = useId();
  const input = useRef<HTMLInputElement>(null);

  // フィルターダイアログで適用・解除した検索語も表示する。
  useEffect(() => {
    if (input.current) input.current.value = query;
  }, [query]);

  return (
    <Box maxW="1200px" mx="auto" mb={3}>
      <form
        aria-label={messages.searchOpinions}
        onSubmit={(event) => {
          event.preventDefault();
          if (input.current) onSearch(input.current.value.trim());
        }}
      >
        <label htmlFor={inputId}>{messages.searchOpinions}</label>
        <Flex gap={2} mt={1} maxW="36rem">
          <Input id={inputId} ref={input} type="search" enterKeyHint="search" minW={0} defaultValue={query} />
          <Button type="submit" variant="outline">
            {messages.searchAction}
          </Button>
        </Flex>
        <Flex align="center" gap={2} wrap="wrap">
          <Text aria-live="polite" aria-atomic="true" fontSize="sm" overflowWrap="anywhere">
            {query && messages.opinionSearchMatches(query, matchCount)}
          </Text>
          {query && (
            <Button
              type="button"
              size="sm"
              variant="plain"
              onClick={() => {
                onSearch("");
                input.current?.focus();
              }}
            >
              {messages.clearOpinionSearch}
            </Button>
          )}
        </Flex>
      </form>
    </Box>
  );
}
