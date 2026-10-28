import { chartRegistry, ensurePluginsLoaded } from "@/components/charts/plugins";
import { Tooltip } from "@/components/ui/tooltip";
import { useMessages } from "@/lib/i18n/LanguageContext";
import type { Messages } from "@/lib/i18n/messages";
import type { ChartType, Result } from "@/type";
import { Box, Button, HStack, Icon, SegmentGroup, Stack } from "@chakra-ui/react";
import { CogIcon, Filter, FullscreenIcon } from "lucide-react";
import type React from "react";
import type { ComponentType } from "react";
import { useMemo } from "react";

// Ensure plugins are loaded
ensurePluginsLoaded();

/** デフォルトで有効なチャートタイプの一覧 */
export const DEFAULT_ENABLED_CHARTS: ChartType[] = ["scatterAll", "scatterDetail", "scatterDensity", "treemap"];

type Props = {
  selected: string;
  onChange: (value: string) => void;
  onClickDensitySetting: () => void;
  onClickFullscreen: () => void;
  /** Result data for evaluating mode.isDisabled conditions */
  result: Result;
  /** Override for modes that have external disabled conditions (e.g., density filter empty) */
  disabledModeOverrides?: Record<string, boolean>;
  /** List of enabled chart types (undefined = default 3 charts for backward compatibility) */
  enabledCharts?: ChartType[];
  /** Order to display charts (undefined = use enabledCharts order) */
  chartOrder?: ChartType[];
  /** フィルタ（テキスト検索・属性）ダイアログを開く。属性の無いレポートでもテキスト検索に使うため常に表示する */
  onClickAttentionFilter?: () => void;
  showAttentionFilterBadge?: boolean;
  attentionFilterBadgeCount?: number;
};

export type ResolvedChartMode = {
  id: string;
  label: string;
  icon: ComponentType;
  isDisabled: boolean;
  /** 無効時の理由、または有効時は読者の目的（「全部読む」など）。両方無いときは undefined */
  tooltip?: string;
};

/**
 * 表示可能なチャートモードを enabledCharts / chartOrder で絞り込み・並べ替え、
 * プラグインの isDisabled と親からの上書きを合わせて無効状態を決める。
 * 通常のモード選択と全画面ツールバーで同じ判定を共有する。
 */
export function resolveChartModes(
  result: Result,
  enabledCharts?: ChartType[],
  chartOrder?: ChartType[],
  disabledModeOverrides: Record<string, boolean> = {},
): ResolvedChartMode[] {
  const allModes = chartRegistry.getAllModes();
  const enabled = enabledCharts ?? DEFAULT_ENABLED_CHARTS;
  const order = chartOrder ?? enabled;

  // Filter modes by enabledCharts
  const enabledModes = allModes.filter((mode) => enabled.includes(mode.id as ChartType));

  // Sort by chartOrder if provided
  const sortedModes = [...enabledModes].sort((a, b) => {
    const aIndex = order.indexOf(a.id as ChartType);
    const bIndex = order.indexOf(b.id as ChartType);
    // Modes not in order go to the end
    const aOrder = aIndex === -1 ? Number.MAX_SAFE_INTEGER : aIndex;
    const bOrder = bIndex === -1 ? Number.MAX_SAFE_INTEGER : bIndex;
    return aOrder - bOrder;
  });

  return sortedModes.map((mode) => {
    // Evaluate disabled state from multiple sources:
    // 1. Plugin's isDisabled function (based on result data structure)
    // 2. Parent's override (e.g., density filter produces empty results)
    const pluginDisabled = mode.isDisabled?.(result) ?? false;
    const overrideDisabled = disabledModeOverrides[mode.id] ?? false;
    const isDisabled = pluginDisabled || overrideDisabled;
    const tooltip = isDisabled && mode.disabledTooltip ? mode.disabledTooltip : undefined;
    return { id: mode.id, label: mode.label, icon: mode.icon, isDisabled, tooltip };
  });
}

/**
 * モード名と説明を表示言語の辞書で上書きする。通常のモード選択と全画面の粒度切替で共有する。
 * 組み込みモードは messages を優先し、外部プラグインは manifest の文言（mode.label / mode.tooltip）をそのまま使う。
 * 有効なモードの tooltip は「読者の目的」（全体をざっくり掴む / 全部読む など）。view は手法名ではなく目的で選ばせる。
 */
export function localizeChartMode(mode: ResolvedChartMode, messages: Messages): ResolvedChartMode {
  return {
    ...mode,
    label: messages.chartModes[mode.id] ?? mode.label,
    tooltip: mode.isDisabled
      ? (messages.chartModeDisabled[mode.id] ?? mode.tooltip)
      : (messages.chartModePurpose[mode.id] ?? mode.tooltip),
  };
}

const SegmentItemWithIcon = (icon: ComponentType, text: string, selected: boolean, tooltip?: string) => {
  const item = (
    <Stack
      direction={["column", null, "row"]}
      gap={2}
      alignItems="center"
      justifyContent="center"
      px={4}
      py={2}
      position="absolute"
      top={0}
      left={0}
      right={0}
      bottom={0}
      color="gray.500"
    >
      <Icon as={icon} />
      <Box fontSize={["14px", null, "16px"]} fontWeight={selected ? "bold" : "normal"} lineHeight="1" textWrap="nowrap">
        {text}
      </Box>
    </Stack>
  );
  // SegmentGroup.Items は tooltip を受け取らないので、ラベル側で包む
  return tooltip ? (
    <Tooltip content={tooltip} openDelay={300} closeDelay={0}>
      {item}
    </Tooltip>
  ) : (
    item
  );
};

export function SelectChartButton({
  selected,
  onChange,
  onClickDensitySetting,
  onClickFullscreen,
  result,
  disabledModeOverrides = {},
  enabledCharts,
  chartOrder,
  onClickAttentionFilter,
  showAttentionFilterBadge,
  attentionFilterBadgeCount,
}: Props) {
  const messages = useMessages();
  // Generate items from plugin registry, filtered by enabledCharts
  const items = useMemo(() => {
    // resolveChartModes で並び順・無効判定を一元化し、文言だけ表示言語の辞書で上書きする。
    return resolveChartModes(result, enabledCharts, chartOrder, disabledModeOverrides)
      .map((mode) => localizeChartMode(mode, messages))
      .map((mode) => ({
        value: mode.id,
        label: SegmentItemWithIcon(mode.icon, mode.label, selected === mode.id, mode.tooltip),
        isDisabled: mode.isDisabled,
      }));
  }, [selected, result, disabledModeOverrides, enabledCharts, chartOrder, messages]);

  // Calculate dynamic tab width based on mode count
  const modeCount = items.length;
  const tabWidth = useMemo(() => {
    // On mobile, tabs fill 100% width divided by count
    // On desktop, use fixed width per tab
    return [`calc(100% / ${modeCount})`, null, "162px"];
  }, [modeCount]);

  const handleChange = (event: React.FormEvent<HTMLDivElement>) => {
    const value = (event.target as HTMLInputElement).value;
    onChange(value);
  };

  return (
    <Box maxW="1200px" mx="auto" mb={2}>
      <Box display="grid" gridTemplateColumns={["1fr", null, "1fr auto"]} gap="3">
        <SegmentGroup.Root
          id="chart-type-selector"
          value={selected}
          onChange={handleChange}
          size="md"
          justifySelf={["center", null, "left", "center"]}
          ml={[0, null, null, "104px"]}
          w={["100%", null, "auto"]}
          h={["80px", null, "56px"]}
        >
          <SegmentGroup.Indicator bg="white" border="1px solid #E4E4E7" boxShadow="0 4px 6px 0 rgba(0, 0, 0, 0.1)" />
          <SegmentGroup.Items items={items} w={tabWidth} h="100%" cursor="pointer" />
        </SegmentGroup.Root>

        <HStack gap={1} justifySelf={["end"]} alignSelf={"center"}>
          {onClickAttentionFilter && (
            <Tooltip content={messages.filter} openDelay={0} closeDelay={0}>
              <Button aria-label={messages.filter} onClick={onClickAttentionFilter} variant="outline" h={"50px"}>
                <Box display="flex" alignItems="center" gap={1}>
                  <Icon>
                    <Filter size={16} />
                  </Icon>
                  {showAttentionFilterBadge && (
                    <Box as="span" fontSize="xs" bg="cyan.500" color="white" p="1" borderRadius="md" minW="5">
                      {attentionFilterBadgeCount}
                    </Box>
                  )}
                </Box>
              </Button>
            </Tooltip>
          )}

          <Tooltip content={messages.displaySettings} openDelay={0} closeDelay={0}>
            <Button onClick={onClickDensitySetting} variant={"outline"} h={"50px"} w={"50px"} p={0}>
              <Icon as={CogIcon} />
            </Button>
          </Tooltip>

          <Tooltip content={messages.fullscreen} openDelay={0} closeDelay={0}>
            <Button
              aria-label={messages.fullscreen}
              onClick={onClickFullscreen}
              variant={"outline"}
              h={"50px"}
              w={"50px"}
              p={0}
            >
              <Icon as={FullscreenIcon} />
            </Button>
          </Tooltip>
        </HStack>
      </Box>
    </Box>
  );
}
