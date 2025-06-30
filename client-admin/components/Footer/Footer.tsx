import { getApiBaseUrl } from "@/app/utils/api";
import type { Meta } from "@/type";
import { Box, Flex, Text } from "@chakra-ui/react";
import { Button } from "../ui/button";
import { Dialog } from "./Dialog";

export async function Footer() {
  try {
    const metaResponse = await fetch(`${getApiBaseUrl()}/meta/metadata.json`);
    const meta: Meta = await metaResponse.json();

    return (
      <Box as="footer" bg="white" py="5" px="6">
        <Flex maxW="1200px" mx="auto" justifyContent="space-between" alignItems="center">
          <Text textStyle="body/sm" color="font.secondary">
            © 2025 デジタル民主主義2030 | レポート内容はレポーターに帰属します
          </Text>
          <Flex>
            {!meta.isDefault && meta.termsLink && (
              <Button variant="ghost" asChild>
                <a href={meta.termsLink} target="_blank" rel="noopener noreferrer">
                  利用規約
                </a>
              </Button>
            )}
            <Dialog />
          </Flex>
        </Flex>
      </Box>
    );
  } catch (_error) {
    return (
      <p>
        エラー：データの取得に失敗しました
        <br />
        Error: fetch failed to {process.env.NEXT_PUBLIC_API_BASEPATH}.
      </p>
    );
  }
}
