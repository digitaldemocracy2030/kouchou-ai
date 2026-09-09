"use client";

import {
  DialogBackdrop,
  DialogBody,
  DialogCloseTrigger,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogRoot,
  DialogTitle,
} from "@/components/ui/dialog";
import { toaster } from "@/components/ui/toaster";
import type { ChartType, Report, ReportDisplayConfig } from "@/type";
import {
  Box,
  Button,
  Checkbox,
  HStack,
  Heading,
  Input,
  Portal,
  Select,
  Separator,
  Text,
  VStack,
  createListCollection,
} from "@chakra-ui/react";
import { type Dispatch, type SetStateAction, useCallback, useEffect, useState } from "react";
import { fetchVisualizationConfig, updateVisualizationConfig } from "./actions";

const AVAILABLE_CHARTS: { id: ChartType; label: string }[] = [
  { id: "scatterAll", label: "散布図（全体）" },
  { id: "scatterDensity", label: "散布図（密度）" },
  { id: "treemap", label: "ツリーマップ" },
  { id: "hierarchyList", label: "階層リスト" },
];

const DEFAULT_CONFIG: ReportDisplayConfig = {
  version: "1",
  enabledCharts: ["scatterAll", "scatterDensity", "treemap"],
  defaultChart: "scatterAll",
};

type VisualizationConfigDialogProps = {
  report: Report;
  isOpen: boolean;
  setIsVisualizationConfigDialogOpen: Dispatch<SetStateAction<boolean>>;
};

export function VisualizationConfigDialog({
  report,
  isOpen,
  setIsVisualizationConfigDialogOpen,
}: VisualizationConfigDialogProps) {
  const [config, setConfig] = useState<ReportDisplayConfig | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const fetchInitialConfig = useCallback(async () => {
    setIsLoading(true);
    const result = await fetchVisualizationConfig(report.slug);
    if (!result.success) {
      toaster.create({
        type: "error",
        title: "エラー",
        description: "可視化設定の取得に失敗しました。",
      });
      setConfig(null);
      setIsVisualizationConfigDialogOpen(false);
    } else {
      setConfig(result.config || DEFAULT_CONFIG);
    }
    setIsLoading(false);
  }, [report.slug, setIsVisualizationConfigDialogOpen]);

  useEffect(() => {
    if (isOpen) {
      fetchInitialConfig();
    } else {
      setConfig(null);
    }
  }, [fetchInitialConfig, isOpen]);

  if (!config) {
    return null;
  }

  return (
    <Dialog
      config={config}
      setConfig={setConfig}
      report={report}
      isOpen={isOpen}
      setIsOpen={setIsVisualizationConfigDialogOpen}
      isLoading={isLoading}
    />
  );
}

type DialogProps = {
  config: ReportDisplayConfig;
  setConfig: Dispatch<SetStateAction<ReportDisplayConfig | null>>;
  report: Report;
  isOpen: boolean;
  setIsOpen: Dispatch<SetStateAction<boolean>>;
  isLoading: boolean;
};

function Dialog({ config, setConfig, report, isOpen, setIsOpen, isLoading }: DialogProps) {
  const [isSaving, setIsSaving] = useState(false);
  const [densityPercent, setDensityPercent] = useState(
    String((config.params?.scatterDensity?.maxDensity ?? 0.2) * 100),
  );
  const [minSamples, setMinSamples] = useState(String(config.params?.scatterDensity?.minValue ?? 5));
  const density = Number(densityPercent);
  const samples = Number(minSamples);
  const densityValid = densityPercent.trim() !== "" && Number.isFinite(density) && density >= 0 && density <= 100;
  const samplesValid = minSamples.trim() !== "" && Number.isSafeInteger(samples) && samples >= 0;
  const thresholdsValid = densityValid && samplesValid;

  const enabledChartsSet = new Set(config.enabledCharts);

  const handleChartToggle = (chartId: ChartType, checked: boolean) => {
    const newEnabledCharts = checked
      ? [...config.enabledCharts, chartId]
      : config.enabledCharts.filter((id) => id !== chartId);

    // If we're disabling the default chart, update the default
    let newDefaultChart = config.defaultChart;
    if (!checked && config.defaultChart === chartId) {
      newDefaultChart = newEnabledCharts[0] || undefined;
    }

    setConfig({
      ...config,
      enabledCharts: newEnabledCharts,
      defaultChart: newDefaultChart,
    });
  };

  const handleDefaultChartChange = (chartId: ChartType) => {
    setConfig({
      ...config,
      defaultChart: chartId,
    });
  };

  const defaultChartCollection = createListCollection({
    items: config.enabledCharts.map((chartId) => {
      const chart = AVAILABLE_CHARTS.find((c) => c.id === chartId);
      return { label: chart?.label || chartId, value: chartId };
    }),
  });

  async function handleSubmit() {
    if (!thresholdsValid) return;
    setIsSaving(true);
    const result = await updateVisualizationConfig(report.slug, {
      ...config,
      params: {
        ...config.params,
        scatterDensity: { ...config.params?.scatterDensity, maxDensity: density / 100, minValue: samples },
      },
    });

    if (!result.success) {
      toaster.create({
        type: "error",
        title: "更新エラー",
        description: result.error || "可視化設定の更新に失敗しました",
      });
      setIsSaving(false);
      return;
    }

    toaster.create({
      type: "success",
      title: "更新完了",
      description: "可視化設定が更新されました",
    });

    setIsSaving(false);
    setIsOpen(false);
  }

  return (
    <DialogRoot
      placement="center"
      open={isOpen}
      modal={true}
      closeOnInteractOutside={true}
      trapFocus={true}
      scrollBehavior="inside"
    >
      <Portal>
        <DialogBackdrop />
        <DialogContent>
          <DialogCloseTrigger onClick={() => setIsOpen(false)} />
          <DialogHeader>
            <DialogTitle>可視化設定</DialogTitle>
          </DialogHeader>
          <DialogBody>
            <VStack gap={4} align="stretch">
              <Box>
                <Heading size="md" mb={3}>
                  表示するチャート
                </Heading>
                <Text mb={3} color="fg.muted" fontSize="sm">
                  レポートに表示するチャートの種類を選択してください。
                </Text>
                <VStack align="stretch" gap={2}>
                  {AVAILABLE_CHARTS.map((chart) => (
                    <HStack key={chart.id} justify="space-between">
                      <Checkbox.Root
                        checked={enabledChartsSet.has(chart.id)}
                        onCheckedChange={(e) => handleChartToggle(chart.id, !!e.checked)}
                        disabled={enabledChartsSet.size === 1 && enabledChartsSet.has(chart.id)}
                      >
                        <Checkbox.HiddenInput />
                        <Checkbox.Control />
                        <Checkbox.Label>{chart.label}</Checkbox.Label>
                      </Checkbox.Root>
                    </HStack>
                  ))}
                </VStack>
              </Box>

              <Box>
                <Heading size="md" mb={3}>
                  濃いクラスタの初期値
                </Heading>
                <Text mb={3} color="fg.muted" fontSize="sm">
                  レポートを開いたときの絞り込み条件です。閲覧者は表示中に変更できます。
                </Text>
                <Text as="label" htmlFor="density-percent">
                  表示する密度の上位割合（%）
                </Text>
                <Input
                  id="density-percent"
                  type="number"
                  min={0}
                  max={100}
                  step="any"
                  value={densityPercent}
                  onChange={(e) => setDensityPercent(e.target.value)}
                  aria-invalid={!densityValid}
                />
                {!densityValid && (
                  <Text role="alert" color="red.600">
                    0〜100の数値を入力してください。
                  </Text>
                )}
                <Text as="label" htmlFor="density-min-samples" mt={3} display="block">
                  意見グループの最小サンプル数
                </Text>
                <Input
                  id="density-min-samples"
                  type="number"
                  min={0}
                  step={1}
                  value={minSamples}
                  onChange={(e) => setMinSamples(e.target.value)}
                  aria-invalid={!samplesValid}
                />
                {!samplesValid && (
                  <Text role="alert" color="red.600">
                    0以上の整数を入力してください。
                  </Text>
                )}
              </Box>

              <Separator my={2} />

              <Box>
                <Heading size="md" mb={3}>
                  デフォルト表示
                </Heading>
                <Text mb={3} color="fg.muted" fontSize="sm">
                  レポートを開いたときに最初に表示されるチャートを選択してください。
                </Text>
                {config.enabledCharts.length > 0 && (
                  <Select.Root
                    collection={defaultChartCollection}
                    value={config.defaultChart ? [config.defaultChart] : []}
                    onValueChange={(item) => {
                      if (item.value[0]) {
                        handleDefaultChartChange(item.value[0] as ChartType);
                      }
                    }}
                  >
                    <Select.HiddenSelect />
                    <Select.Control>
                      <Select.Trigger>
                        <Select.ValueText placeholder="デフォルトチャートを選択" />
                      </Select.Trigger>
                      <Select.IndicatorGroup>
                        <Select.Indicator />
                      </Select.IndicatorGroup>
                    </Select.Control>
                    <Select.Positioner>
                      <Select.Content>
                        {defaultChartCollection.items.map((item) => (
                          <Select.Item item={item} key={item.value}>
                            {item.label}
                            <Select.ItemIndicator />
                          </Select.Item>
                        ))}
                      </Select.Content>
                    </Select.Positioner>
                  </Select.Root>
                )}
              </Box>
            </VStack>
          </DialogBody>
          <DialogFooter>
            <Button variant="outline" onClick={() => setIsOpen(false)}>
              キャンセル
            </Button>
            <Button
              onClick={handleSubmit}
              loading={isSaving}
              disabled={config.enabledCharts.length === 0 || !thresholdsValid}
            >
              保存
            </Button>
          </DialogFooter>
        </DialogContent>
      </Portal>
    </DialogRoot>
  );
}
