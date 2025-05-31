"use client";

import type { Meta } from "@/type";
import { Box, Button, Flex, Link, Text } from "@chakra-ui/react";
import { Globe } from "lucide-react";
import { type ReactNode, useState } from "react";

function EmptyText() {
  return (
    <Text fontSize="sm" color="gray.500">
      レポーター情報が未設定です。レポート作成者が
      <Link
        href="https://github.com/digitaldemocracy2030/kouchou-ai/blob/main/README.md#%E3%83%A1%E3%82%BF%E3%83%87%E3%83%BC%E3%82%BF%E3%83%95%E3%82%A1%E3%82%A4%E3%83%AB%E3%81%AE%E3%82%BB%E3%83%83%E3%83%88%E3%82%A2%E3%83%83%E3%83%97"
        target="_blank"
        rel="noopener noreferrer"
        variant="underline"
        color="currentcolor"
        _hover={{
          color: "gray.400",
        }}
      >
        メタデータをセットアップ
      </Link>
      することでレポーター情報が表示されます。
    </Text>
  );
}

function ReadMore({ setIsExpanded }: { setIsExpanded: (isExpanded: boolean) => void }) {
  return (
    <Flex display="inline-flex">
      <Text w="1rem">...</Text>
      <Button
        variant="plain"
        w="fit-content"
        h="fit-content"
        p="0"
        mt="2px"
        color="blue.500"
        fontWeight="normal"
        textDecoration="underline"
        textUnderlineOffset="2px"
        _hover={{
          opacity: 0.75,
          textDecoration: "none",
        }}
        onClick={() => setIsExpanded(true)}
      >
        全文表示
      </Button>
    </Flex>
  );
}

function MessageText({ isDefault, message }: { isDefault: boolean; message: string }) {
  const TRUNCATED_TEXT_LENGTH = 55;
  const messageWithoutNewLines = message.replace(/\n/g, '');
  const isTruncated = messageWithoutNewLines.length > TRUNCATED_TEXT_LENGTH;
  const [isExpanded, setIsExpanded] = useState(!isTruncated);

  // metdataが未設定の場合は、設定方法を案内するテキストを表示
  if (isDefault) {
    return <EmptyText />;
  }

  return (
    <Text
      as="div"
      fontSize="sm"
      lineHeight={2}
      color="gray.600"
      textAlign="left"
      whiteSpace={isExpanded ? "pre-line" : "normal"}
      wordBreak={isExpanded ? "normal" : "break-all"}
    >
      {!isExpanded ? messageWithoutNewLines.slice(0, TRUNCATED_TEXT_LENGTH) : message}
      {!isExpanded && <ReadMore setIsExpanded={setIsExpanded} />}
    </Text>
  );
}

export function ReporterContent({ meta, children }: { meta: Meta; children: ReactNode }) {
  return (
    <Flex flexDirection="column" gap="4" color="gray.600">
      <Flex flexDirection={{ base: "column", md: "row" }} alignItems="flex-start">
        <Box mb={{ base: "4", md: "0" }} mr={{ base: "0", md: "4" }} _empty={{ display: "none" }}>
          {children}
        </Box>
        <Flex flexDirection="column" justifyContent="space-between" color="gray.600" gap="2">
          <Text fontSize="xs">レポーター</Text>
          {/* metadataが未設定の場合は、レポーター名は非表示 */}
          {!meta.isDefault && (
            <Text fontSize="md" fontWeight="bold">
              {meta.reporter}
            </Text>
          )}
        </Flex>
      </Flex>
      {!meta.isDefault && meta.message && <MessageText isDefault={meta.isDefault} message={meta.message} />}
      <Flex gap="3" flexWrap="wrap" w="fit-content" _empty={{ display: "none" }}>
        {!meta.isDefault && meta.webLink && (
          <Button
            variant="outline"
            size="xs"
            rounded="full"
            px="5"
            color="currentcolor"
            _icon={{
              width: "14px",
              height: "14px",
            }}
            asChild
          >
            <a href={meta.webLink} target="_blank" rel="noopener noreferrer">
              <Flex gap="1" alignItems="center">
                <Globe />
                ウェブページ
              </Flex>
            </a>
          </Button>
        )}
        {!meta.isDefault && meta.privacyLink && (
          <Button variant="outline" size="xs" rounded="full" px="5" color="currentcolor" asChild>
            <a href={meta.privacyLink} target="_blank" rel="noopener noreferrer">
              プライバシーポリシー
            </a>
          </Button>
        )}
        {!meta.isDefault && meta.termsLink && (
          <Button variant="outline" size="xs" rounded="full" px="5" color="currentcolor" asChild>
            <a href={meta.termsLink} target="_blank" rel="noopener noreferrer">
              利用規約
            </a>
          </Button>
        )}
      </Flex>
    </Flex>
  );
}
