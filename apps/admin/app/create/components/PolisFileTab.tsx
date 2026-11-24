import { Box, Button, Field, Input, Tabs, Text, VStack } from "@chakra-ui/react";
import { useRef, useState } from "react";
import type { useClusterSettings } from "../hooks/useClusterSettings";
import { type PolisImport, readPolisExport } from "../polisImport";
import { AttributeColumnsSelector } from "./AttributeColumnsSelector";
import { ClusterSettingsSection } from "./ClusterSettingsSection";
import { PolisParticipantPlot } from "./PolisParticipantPlot";

function PolisCsvInput({
  label,
  file,
  disabled,
  onChange,
}: {
  label: string;
  file: File | null;
  disabled: boolean;
  onChange: (file: File | null) => void;
}) {
  const input = useRef<HTMLInputElement>(null);
  return (
    <Field.Root>
      <Field.Label>{label}</Field.Label>
      <Input
        ref={input}
        type="file"
        accept=".csv,text/csv"
        disabled={disabled}
        onChange={(event) => onChange(event.target.files?.[0] ?? null)}
      />
      {file && (
        <Button
          size="xs"
          variant="outline"
          mt={2}
          disabled={disabled}
          onClick={() => {
            if (input.current) input.current.value = "";
            onChange(null);
          }}
        >
          {label}を外す
        </Button>
      )}
    </Field.Root>
  );
}

export function PolisFileTab({
  data,
  onDataChange,
  selectedAttributes,
  onAttributesChange,
  clusterSettings,
}: {
  data: PolisImport | null;
  onDataChange: (data: PolisImport | null) => void;
  selectedAttributes: string[];
  onAttributesChange: (attributes: string[]) => void;
  clusterSettings: ReturnType<typeof useClusterSettings>;
}) {
  const [comments, setComments] = useState<File | null>(null);
  const [votes, setVotes] = useState<File | null>(null);
  const [history, setHistory] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showPlot, setShowPlot] = useState(false);

  const clearResult = () => {
    onDataChange(null);
    setError(null);
    setShowPlot(false);
  };

  const load = async () => {
    if (!comments || loading) return;
    clearResult();
    setLoading(true);
    try {
      onDataChange(await readPolisExport(comments, votes, history));
    } catch (error) {
      setError(error instanceof Error ? error.message : "PolisのCSVを読み込めませんでした。");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Tabs.Content value="polis">
      <VStack align="stretch" gap={4}>
        <PolisCsvInput
          label="コメント（comments.csv）"
          file={comments}
          disabled={loading}
          onChange={(file) => {
            setComments(file);
            clearResult();
          }}
        />
        <PolisCsvInput
          label="参加者別投票（任意）"
          file={votes}
          disabled={loading}
          onChange={(file) => {
            setVotes(file);
            clearResult();
          }}
        />
        <PolisCsvInput
          label="投票履歴（任意）"
          file={history}
          disabled={loading}
          onChange={(file) => {
            setHistory(file);
            clearResult();
          }}
        />
        <Text fontSize="sm" color="fg.muted">
          同じ会話・同じ時点の participants-votes.csv でPolisグループを、votes.csv で投票の推移を表示できます。
        </Text>
        <Button alignSelf="start" variant="outline" disabled={!comments} loading={loading} onClick={load}>
          Polisデータを読み込む
        </Button>
        {error && (
          <Text color="red.600" role="alert">
            {error}
          </Text>
        )}
        {data && (
          <Box>
            <Box aria-live="polite">
              <Text>
                分析対象 {data.comments.length} 件／Polisで除外済み {data.excluded} 件／本文が空欄 {data.blank} 件
              </Text>
              {data.voteSource !== "comments" && <Text>投票CSVと照合できた分析対象 {data.matchedComments} 件</Text>}
              {data.voteSource === "matrix" && <Text>Polisの参加者グループ {data.groups} 個</Text>}
              {data.comments.length === 0 && <Text>分析できるコメントがありません。</Text>}
            </Box>
            {data.participantVotes && data.comments.length > 0 && (
              <Box mt={4}>
                <Button variant="outline" aria-expanded={showPlot} onClick={() => setShowPlot(!showPlot)}>
                  {showPlot ? "参加者の散布図を閉じる" : "参加者の散布図を開く"}
                </Button>
                {showPlot && <PolisParticipantPlot votes={data.participantVotes} comments={data.comments} />}
              </Box>
            )}
            {data.attributeColumns.length > 0 && (
              <>
                <AttributeColumnsSelector
                  columns={data.attributeColumns}
                  selectedColumn="comment-body"
                  selectedAttributes={selectedAttributes}
                  onAttributeChange={onAttributesChange}
                />
                <Text fontSize="sm" mt={2}>
                  選んだ票数は元コメント単位でレポートの絞り込みに使えます。レポートを公開すると、選んだ票数も公開されます。
                </Text>
              </>
            )}
          </Box>
        )}
        {data && data.comments.length > 0 && (
          <ClusterSettingsSection
            clusterLv1={clusterSettings.clusterLv1}
            clusterLv2={clusterSettings.clusterLv2}
            recommendedClusters={clusterSettings.recommendedClusters}
            autoAdjusted={clusterSettings.autoAdjusted}
            onLv1Change={clusterSettings.handleLv1Change}
            onLv2Change={clusterSettings.handleLv2Change}
          />
        )}
      </VStack>
    </Tabs.Content>
  );
}
