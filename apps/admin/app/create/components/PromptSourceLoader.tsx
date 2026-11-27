"use client";

import { Box, Button, Field, HStack, NativeSelect, Text, VStack } from "@chakra-ui/react";
import { useCallback, useEffect, useRef, useState } from "react";
import { listPromptSourceReports } from "../api/promptSources";
import type { usePromptSettings } from "../hooks/usePromptSettings";
import {
  type PromptKey,
  type PromptLoadPlan,
  type PromptSourceReport,
  type PromptValues,
  type ReportPromptConfig,
  editedSinceLoad,
  formatPromptKeys,
  planPromptLoad,
  promptSourceLabel,
  sortPromptSourceReports,
} from "../utils/promptsFromReport";

type PromptSettings = Pick<
  ReturnType<typeof usePromptSettings>,
  | "extraction"
  | "initialLabelling"
  | "mergeLabelling"
  | "overview"
  | "setExtraction"
  | "setInitialLabelling"
  | "setMergeLabelling"
  | "setOverview"
>;

type LoadedFrom = {
  label: string;
  values: PromptValues;
  loaded: PromptKey[];
  missing: PromptKey[];
};

type PendingLoad = {
  label: string;
  config: ReportPromptConfig;
  plan: PromptLoadPlan;
};

const CONFIG_ERROR = "設定の取得に失敗しました";

async function fetchReportConfig(slug: string): Promise<ReportPromptConfig> {
  const response = await fetch(`/api/admin/reports/${encodeURIComponent(slug)}/config`);
  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || CONFIG_ERROR);
  }
  const data = await response.json();
  if (!data?.config) {
    throw new Error(CONFIG_ERROR);
  }
  return data.config as ReportPromptConfig;
}

/**
 * 既存のレポートを手本に、プロンプトだけを読み込む（#1203）。
 * 入力データや他の設定は読み込まない。読み込んだ後もプロンプトは個別に編集できる。
 */
export function PromptSourceLoader({ promptSettings }: { promptSettings: PromptSettings }) {
  const [reports, setReports] = useState<PromptSourceReport[] | null>(null);
  const [listError, setListError] = useState<string | null>(null);
  const [selected, setSelected] = useState("");
  const [loadingConfig, setLoadingConfig] = useState(false);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [pending, setPending] = useState<PendingLoad | null>(null);
  const [loadedFrom, setLoadedFrom] = useState<LoadedFrom | null>(null);
  const requestId = useRef(0);

  const current: PromptValues = {
    extraction: promptSettings.extraction,
    initialLabelling: promptSettings.initialLabelling,
    mergeLabelling: promptSettings.mergeLabelling,
    overview: promptSettings.overview,
  };
  // 設定の取得を待つ間に編集された内容も、上書きの確認に含める
  const latest = useRef(current);
  latest.current = current;

  const loadReports = useCallback(async () => {
    setReports(null);
    setListError(null);
    try {
      const result = await listPromptSourceReports();
      if (result.success) {
        setReports(sortPromptSourceReports(result.reports));
      } else {
        setListError(result.error);
      }
    } catch {
      setListError("レポート一覧の取得に失敗しました");
    }
  }, []);

  useEffect(() => {
    loadReports();
  }, [loadReports]);

  const apply = (label: string, plan: PromptLoadPlan) => {
    if (plan.loaded.includes("extraction")) promptSettings.setExtraction(plan.next.extraction);
    if (plan.loaded.includes("initialLabelling")) promptSettings.setInitialLabelling(plan.next.initialLabelling);
    if (plan.loaded.includes("mergeLabelling")) promptSettings.setMergeLabelling(plan.next.mergeLabelling);
    if (plan.loaded.includes("overview")) promptSettings.setOverview(plan.next.overview);
    setLoadedFrom({ label, values: plan.next, loaded: plan.loaded, missing: plan.missing });
    setPending(null);
  };

  // 確認を出している間もプロンプト欄は編集できるので、「上書きする」の時点の値で計画し直す。
  // 確認した時には無かった上書きが増えていたら、確認を出し直す。
  const confirmOverwrite = (confirmed: PendingLoad) => {
    const plan = planPromptLoad(latest.current, confirmed.config);
    const added = plan.overwritten.filter((key) => !confirmed.plan.overwritten.includes(key));
    if (added.length > 0) {
      setPending({ ...confirmed, plan });
    } else {
      apply(confirmed.label, plan);
    }
  };

  const handleLoad = async () => {
    const source = reports?.find((report) => report.slug === selected);
    if (!source) return;
    const label = promptSourceLabel(source);
    const id = ++requestId.current;
    setLoadingConfig(true);
    setLoadError(null);
    setPending(null);
    try {
      const config = await fetchReportConfig(source.slug);
      if (id !== requestId.current) return;
      const plan = planPromptLoad(latest.current, config);
      if (plan.loaded.length === 0) {
        setLoadError(`「${label}」にはプロンプトが保存されていません。今の内容のままです。`);
      } else if (plan.overwritten.length > 0) {
        setPending({ label, config, plan });
      } else {
        apply(label, plan);
      }
    } catch (error) {
      if (id !== requestId.current) return;
      const message = error instanceof Error ? error.message : CONFIG_ERROR;
      setLoadError(`「${label}」の設定を取得できませんでした（${message}）。プロンプトは変わっていません。`);
    } finally {
      if (id === requestId.current) setLoadingConfig(false);
    }
  };

  const edited = loadedFrom ? editedSinceLoad(current, loadedFrom.values, loadedFrom.loaded) : [];
  const noReports = reports !== null && reports.length === 0;

  return (
    <Box w="full" borderWidth="1px" borderRadius="md" p={4}>
      <Field.Root>
        <Field.Label>既存のレポートからプロンプトを読み込む</Field.Label>
        <HStack w="full" align="flex-start">
          <NativeSelect.Root flex="1" disabled={reports === null || noReports || loadingConfig}>
            <NativeSelect.Field
              aria-label="プロンプトを読み込むレポート"
              value={selected}
              onChange={(e) => {
                setSelected(e.target.value);
                setLoadError(null);
                setPending(null);
              }}
            >
              <option value="">
                {reports === null && !listError ? "読み込み中です…" : "レポートを選んでください"}
              </option>
              {reports?.map((report) => (
                <option key={report.slug} value={report.slug}>
                  {promptSourceLabel(report)}
                </option>
              ))}
            </NativeSelect.Field>
            <NativeSelect.Indicator />
          </NativeSelect.Root>
          <Button variant="outline" onClick={handleLoad} loading={loadingConfig} disabled={!selected || !!pending}>
            読み込む
          </Button>
        </HStack>
        <Field.HelperText>
          調整したプロンプトを、作成済みのレポートから読み込みます。入力データや他の設定は読み込みません。読み込んだ後も編集できます。
        </Field.HelperText>
      </Field.Root>

      {listError && (
        <HStack mt={3} gap={3}>
          <Text color="red.500" fontSize="sm">
            レポート一覧を取得できませんでした（{listError}）。
          </Text>
          <Button size="xs" variant="outline" onClick={loadReports}>
            再試行
          </Button>
        </HStack>
      )}

      {noReports && (
        <Text mt={3} fontSize="sm" color="font.secondary">
          読み込めるレポートがまだありません。
        </Text>
      )}

      {loadError && (
        <Text mt={3} color="red.500" fontSize="sm" role="alert">
          {loadError}
        </Text>
      )}

      {pending && (
        <VStack mt={3} p={3} align="stretch" gap={2} borderWidth="1px" borderColor="orange.300" borderRadius="md">
          <Text fontSize="sm">
            {`入力済みの${formatPromptKeys(pending.plan.overwritten)}プロンプトを「${pending.label}」の内容で上書きします。よろしいですか？`}
          </Text>
          <HStack>
            <Button size="sm" colorPalette="orange" onClick={() => confirmOverwrite(pending)}>
              上書きする
            </Button>
            <Button size="sm" variant="outline" onClick={() => setPending(null)}>
              やめる
            </Button>
          </HStack>
        </VStack>
      )}

      {loadedFrom && !pending && (
        <VStack mt={3} align="stretch" gap={1}>
          <Text fontSize="sm">
            「{loadedFrom.label}」から{formatPromptKeys(loadedFrom.loaded)}プロンプトを読み込みました。
          </Text>
          {loadedFrom.missing.length > 0 && (
            <Text fontSize="sm" color="font.secondary">
              {`${formatPromptKeys(loadedFrom.missing)}プロンプトはこのレポートに保存されていないため、今の内容のままです。`}
            </Text>
          )}
          {edited.length > 0 && (
            <Text fontSize="sm" color="font.secondary">
              読み込んだ後に{formatPromptKeys(edited)}プロンプトを編集しています。
            </Text>
          )}
        </VStack>
      )}
    </Box>
  );
}
