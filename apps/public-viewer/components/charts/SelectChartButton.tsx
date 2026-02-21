import { chartRegistry, ensurePluginsLoaded } from "@/components/charts/plugins";
import { Tooltip } from "@/components/ui/tooltip";
import type { ChartType, Result } from "@/type";
import { Box, Button, HStack, Icon, SegmentGroup, Stack } from "@chakra-ui/react";
import { CogIcon, Filter, FullscreenIcon } from "lucide-react";
import type React from "react";
import type { ComponentType } from "react";
import { useMemo } from "react";

// Ensure plugins are loaded
ensurePluginsLoaded();

/** Default enabled charts (maintains backward compatibility) */
const DEFAULT_ENABLED_CHARTS: ChartType[] = ["scatterAll", "scatterDetail", "scatterDensity", "treemap"];

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
  onClickAttentionFilter?: () => void;
  isAttentionFilterEnabled?: boolean;
  showAttentionFilterBadge?: boolean;
  attentionFilterBadgeCount?: number;
};

const SegmentItemWithIcon = (icon: ComponentType, text: string, selected: boolean) => {
  return (
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
  isAttentionFilterEnabled,
  showAttentionFilterBadge,
  attentionFilterBadgeCount,
}: Props) {
  // Generate items from plugin registry, filtered by enabledCharts
  const items = useMemo(() => {
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

      return {
        value: mode.id,
        label: SegmentItemWithIcon(mode.icon, mode.label, selected === mode.id),
        isDisabled,
        tooltip,
      };
    });
  }, [selected, result, disabledModeOverrides, enabledCharts, chartOrder]);

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
          {isAttentionFilterEnabled && onClickAttentionFilter && (
            <Tooltip content={"フィルタ"} openDelay={0} closeDelay={0}>
              <Button onClick={onClickAttentionFilter} variant="outline" h={"50px"}>
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

          <Tooltip content={"表示設定"} openDelay={0} closeDelay={0}>
            <Button onClick={onClickDensitySetting} variant={"outline"} h={"50px"} w={"50px"} p={0}>
              <Icon as={CogIcon} />
            </Button>
          </Tooltip>

          <Tooltip content={"全画面表示"} openDelay={0} closeDelay={0}>
            <Button onClick={onClickFullscreen} variant={"outline"} h={"50px"} w={"50px"} p={0}>
              <Icon as={FullscreenIcon} />
            </Button>
          </Tooltip>
        </HStack>
      </Box>
    </Box>
  );
}
