import { Button, Field, HStack, Input, Tabs, Text, VStack } from "@chakra-ui/react";
import type { useClusterSettings } from "../hooks/useClusterSettings";
import type { SpreadsheetComment } from "../types";
import { AttributeColumnsSelector } from "./AttributeColumnsSelector";
import { ClusterSettingsSection } from "./ClusterSettingsSection";
import { CommentColumnSelector } from "./CommentColumnSelector";

// スプレッドシートタブコンポーネント
export function SpreadsheetTab({
  spreadsheetUrl,
  setSpreadsheetUrl,
  spreadsheetImported,
  spreadsheetLoading,
  spreadsheetData,
  importedId,
  canImport,
  csvColumns,
  selectedCommentColumn,
  setSelectedCommentColumn,
  selectedAttributeColumns,
  setSelectedAttributeColumns,
  clusterSettings,
  onImport,
  onClearData,
}: {
  spreadsheetUrl: string;
  setSpreadsheetUrl: (url: string) => void;
  spreadsheetImported: boolean;
  spreadsheetLoading: boolean;
  spreadsheetData: SpreadsheetComment[];
  importedId: string;
  canImport: boolean; // 型を明示的にbooleanに修正
  csvColumns: string[];
  selectedCommentColumn: string;
  setSelectedCommentColumn: (column: string) => void;
  selectedAttributeColumns: string[];
  setSelectedAttributeColumns: (columns: string[]) => void;
  clusterSettings: ReturnType<typeof useClusterSettings>;
  onImport: () => Promise<void>;
  onClearData: () => Promise<void>;
}) {
  return (
    <Tabs.Content value="spreadsheet">
      <VStack alignItems="stretch" w="full" gap={4}>
        <Field.Root>
          <Field.Label>スプレッドシートURL</Field.Label>
          <HStack
            w="full"
            flexDir={["column", "column", "row"]}
            alignItems={["stretch", "stretch", "center"]}
            gap={[2, 2, 4]}
          >
            <Input
              flex="1"
              value={spreadsheetUrl}
              onChange={(e) => setSpreadsheetUrl(e.target.value)}
              placeholder="https://docs.google.com/spreadsheets/d/xxxxxxxxxxxx/edit"
              disabled={spreadsheetImported}
            />
            <Button
              onClick={onImport}
              loading={spreadsheetLoading}
              disabled={!canImport}
              whiteSpace="nowrap"
              width={["full", "full", "auto"]}
            >
              {spreadsheetImported ? "取得済み" : "データを取得"}
            </Button>
          </HStack>
          <Field.HelperText>
            公開されているGoogleスプレッドシートのURLを入力してください
            <br />
          </Field.HelperText>

          <CommentColumnSelector
            columns={csvColumns}
            selectedColumn={selectedCommentColumn}
            onColumnChange={setSelectedCommentColumn}
          />

          <AttributeColumnsSelector 
            columns={csvColumns}
            selectedColumn={selectedCommentColumn}
            selectedAttributes={selectedAttributeColumns}
            onAttributeChange={setSelectedAttributeColumns}
          />

          <ClusterSettingsSection
            clusterLv1={clusterSettings.clusterLv1}
            clusterLv2={clusterSettings.clusterLv2}
            recommendedClusters={clusterSettings.recommendedClusters}
            autoAdjusted={clusterSettings.autoAdjusted}
            onLv1Change={clusterSettings.handleLv1Change}
            onLv2Change={clusterSettings.handleLv2Change}
          />
        </Field.Root>

        {spreadsheetImported && (
          <Text color="green.500" fontSize="sm">
            スプレッドシートのデータ {spreadsheetData.length} 件を取得しました
          </Text>
        )}

        {spreadsheetImported && (
          <Button
            onClick={onClearData}
            colorScheme="red"
            variant="outline"
            size="sm"
            loading={spreadsheetLoading}
            loadingText="クリア中..."
          >
            データをクリアして再入力
          </Button>
        )}
      </VStack>
    </Tabs.Content>
  );
}
