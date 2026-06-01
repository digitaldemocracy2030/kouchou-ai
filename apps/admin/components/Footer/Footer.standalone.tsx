"use client";

/**
 * Standalone (Windows embeddable) 用の Footer（クライアント描画版）。
 *
 * ホスト版 (Footer.tsx) は async サーバコンポーネントで、ビルド時に /meta/metadata.json を
 * fetch する。静的エクスポートではサーバが無く相対 URL の fetch がビルド時に失敗してエラーが
 * 焼き込まれるため、ビルド時に standalone-prep.mjs がこのファイルを Footer.tsx に差し替える。
 * 実行時に同一オリジンから取得する。
 */

import { getApiBaseUrl } from "@/app/utils/api";
import type { Meta } from "@/type";
import { Box, Flex, Text } from "@chakra-ui/react";
import { useEffect, useState } from "react";
import { Button } from "../ui/button";
import { Dialog } from "./Dialog";

export function Footer() {
  const [meta, setMeta] = useState<Meta | null>(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await fetch(`${getApiBaseUrl()}/meta/metadata.json`);
        if (!res.ok) return;
        const data: Meta = await res.json();
        if (!cancelled) setMeta(data);
      } catch {
        // footer is non-critical; ignore fetch failures
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <Box as="footer" bg="white" py="5" px="6">
      <Flex maxW="1200px" mx="auto" justifyContent="space-between" alignItems="center">
        <Text textStyle="body/sm" color="font.secondary">
          © 2025 デジタル民主主義2030 | レポート内容はレポーターに帰属します
        </Text>
        <Flex>
          {meta && !meta.isDefault && meta.termsLink && (
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
}
