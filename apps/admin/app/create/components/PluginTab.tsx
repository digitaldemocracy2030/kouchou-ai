"use client";

import type { PluginManifest } from "@/type.d";
import { Badge, Box, Button, Field, HStack, Input, Spinner, Text, VStack } from "@chakra-ui/react";
import { LuAlertCircle, LuCheck, LuDownload, LuEye, LuTrash2 } from "react-icons/lu";
import type { PluginState } from "../types";
import { AttributeColumnsSelector } from "./AttributeColumnsSelector";
import { CommentColumnSelector } from "./CommentColumnSelector";

interface PluginTabProps {
  plugin: PluginManifest;
  state: PluginState | undefined;
  csvColumns: string[];
  selectedCommentColumn: string;
  selectedAttributeColumns: string[];
  setSelectedCommentColumn: (column: string) => void;
  setSelectedAttributeColumns: (columns: string[]) => void;
  onUrlChange: (url: string) => void;
  onPreview: () => void;
  onImport: () => void;
  onClear: () => void;
  reportId: string;
}

/**
 * プラグイン入力タブコンポーネント
 * 各プラグイン（YouTube等）の入力UIを提供
 */
export function PluginTab({
  plugin,
  state,
  csvColumns,
  selectedCommentColumn,
  selectedAttributeColumns,
  setSelectedCommentColumn,
  setSelectedAttributeColumns,
  onUrlChange,
  onPreview,
  onImport,
  onClear,
  reportId,
}: PluginTabProps) {
  const isLoading = state?.loading ?? false;
  const isImported = state?.imported ?? false;
  const hasData = (state?.data?.length ?? 0) > 0;
  const url = state?.url ?? "";

  // プラグインが利用不可の場合
  if (!plugin.isAvailable) {
    return (
      <Box p={4} borderWidth="1px" borderRadius="md" bg="orange.50">
        <VStack align="start" gap={3}>
          <HStack>
            <LuAlertCircle color="orange" />
            <Text fontWeight="bold" color="orange.700">
              {plugin.name}は設定が必要です
            </Text>
          </HStack>
          <Text fontSize="sm" color="gray.600">
            {plugin.description}
          </Text>
          <VStack align="start" gap={1} w="full">
            <Text fontSize="sm" fontWeight="medium">
              不足している設定:
            </Text>
            {plugin.missingSettings.map((msg) => (
              <Text key={msg} fontSize="sm" color="red.600">
                • {msg}
              </Text>
            ))}
          </VStack>
          <Text fontSize="xs" color="gray.500">
            管理者に連絡して環境変数を設定してください。
          </Text>
        </VStack>
      </Box>
    );
  }

  // インポート済みの場合
  if (isImported) {
    return (
      <Box p={4} borderWidth="1px" borderRadius="md" bg="green.50">
        <VStack align="start" gap={3}>
          <HStack>
            <LuCheck color="green" />
            <Text fontWeight="bold" color="green.700">
              インポート完了
            </Text>
            <Badge colorPalette="green">{state?.commentCount ?? 0} 件</Badge>
          </HStack>
          <Text fontSize="sm" color="gray.600">
            {url}
          </Text>
          <Button size="sm" variant="outline" colorPalette="red" onClick={onClear}>
            <LuTrash2 />
            クリア
          </Button>
        </VStack>
      </Box>
    );
  }

  return (
    <VStack align="stretch" gap={4}>
      {/* URL入力 */}
      <Field.Root>
        <Field.Label>{plugin.name} URL</Field.Label>
        <Input
          placeholder={getPlaceholder(plugin.id)}
          value={url}
          onChange={(e) => onUrlChange(e.target.value)}
          disabled={isLoading}
        />
        <Field.HelperText>{plugin.description}</Field.HelperText>
      </Field.Root>

      {/* アクションボタン */}
      <HStack>
        <Button size="sm" variant="outline" onClick={onPreview} disabled={!url.trim() || isLoading}>
          {isLoading ? <Spinner size="sm" /> : <LuEye />}
          プレビュー
        </Button>
        <Button size="sm" colorPalette="blue" onClick={onImport} disabled={!url.trim() || isLoading || !reportId}>
          {isLoading ? <Spinner size="sm" /> : <LuDownload />}
          インポート
        </Button>
      </HStack>

      {/* プレビューデータがある場合のカラム選択 */}
      {hasData && csvColumns.length > 0 && (
        <Box p={4} borderWidth="1px" borderRadius="md" bg="gray.50">
          <VStack align="stretch" gap={3}>
            <HStack>
              <Text fontWeight="bold" fontSize="sm">
                プレビュー
              </Text>
              <Badge colorPalette="blue">{state?.commentCount ?? 0} 件</Badge>
            </HStack>

            <CommentColumnSelector
              columns={csvColumns}
              selectedColumn={selectedCommentColumn}
              onColumnChange={setSelectedCommentColumn}
            />

            <AttributeColumnsSelector
              columns={csvColumns}
              selectedCommentColumn={selectedCommentColumn}
              selectedAttributeColumns={selectedAttributeColumns}
              onAttributeColumnsChange={setSelectedAttributeColumns}
            />
          </VStack>
        </Box>
      )}
    </VStack>
  );
}

/**
 * プラグインIDに応じたプレースホルダーテキストを取得
 */
function getPlaceholder(pluginId: string): string {
  switch (pluginId) {
    case "youtube":
      return "https://www.youtube.com/watch?v=... または https://www.youtube.com/playlist?list=...";
    default:
      return "URLを入力してください";
  }
}
