import { FileUploadDropzone, FileUploadList, FileUploadRoot } from "@/components/ui/file-upload";
import { Box, Tabs, VStack } from "@chakra-ui/react";
import { DownloadIcon } from "lucide-react";
import Link from "next/link";
import { useRef, useState } from "react";
import type { useClusterSettings } from "../hooks/useClusterSettings";
import { parseCsv } from "../parseCsv";
import { getBestCommentColumn } from "../utils/columnScorer";
import { AttributeColumnsSelector } from "./AttributeColumnsSelector";
import { ClusterSettingsSection } from "./ClusterSettingsSection";
import { CommentColumnSelector } from "./CommentColumnSelector";

// CSVファイルタブコンポーネント
export function CsvFileTab({
  csv,
  setCsv,
  csvColumns,
  setCsvColumns,
  selectedCommentColumn,
  setSelectedCommentColumn,
  selectedAttributeColumns,
  setSelectedAttributeColumns,
  clusterSettings,
}: {
  csv: File | null;
  setCsv: (file: File | null) => void;
  csvColumns: string[];
  setCsvColumns: (columns: string[]) => void;
  selectedCommentColumn: string;
  setSelectedCommentColumn: (column: string) => void;
  selectedAttributeColumns: string[];
  setSelectedAttributeColumns: (columns: string[]) => void;
  clusterSettings: ReturnType<typeof useClusterSettings>;
}) {
  const [csvError, setCsvError] = useState<string | null>(null);
  const loadVersion = useRef(0);
  return (
    <Tabs.Content value="file">
      <VStack alignItems="stretch" w="full">
        <Link
          href="/sample_comments.csv"
          download
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "4px",
            marginLeft: "8px",
            textDecoration: "underline",
            fontSize: "0.8rem",
          }}
        >
          <DownloadIcon size={14} />
          サンプルCSVをダウンロード
        </Link>
        <FileUploadRoot
          w={"full"}
          alignItems="stretch"
          accept={["text/csv"]}
          inputProps={{ multiple: false }}
          onFileChange={async (e) => {
            const file = e.acceptedFiles[0];
            const version = ++loadVersion.current;
            setCsv(null);
            setCsvError(null);
            setCsvColumns([]);
            setSelectedCommentColumn("");
            setSelectedAttributeColumns([]);
            clusterSettings.resetClusterSettings();
            if (!file) return;
            try {
              const parsed = await parseCsv(file);
              if (version !== loadVersion.current) return;
              const columns = Object.keys(parsed[0]).filter((key) => key !== "id");
              setCsv(file);
              setCsvColumns(columns);
              setSelectedCommentColumn(getBestCommentColumn(parsed as unknown as Record<string, unknown>[]) || "");
              clusterSettings.setRecommended(parsed.length);
            } catch (error) {
              if (version !== loadVersion.current) return;
              setCsvError(
                error instanceof Error ? error.message : "CSVを読み取れませんでした。ファイルを選択し直してください。",
              );
            }
          }}
        >
          <Box opacity={csv ? 0.5 : 1} pointerEvents={csv ? "none" : "auto"}>
            <FileUploadDropzone label="分析するコメントファイルを選択してください" description=".csv" />
          </Box>
          <FileUploadList
            clearable={true}
            onRemove={() => {
              ++loadVersion.current;
              setCsvError(null);
              setSelectedAttributeColumns([]);
              setCsv(null);
              setCsvColumns([]);
              setSelectedCommentColumn("");
              clusterSettings.resetClusterSettings();
            }}
          />
        </FileUploadRoot>

        {csvError && (
          <Box role="alert" color="red.600">
            {csvError}
          </Box>
        )}

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
      </VStack>
    </Tabs.Content>
  );
}
