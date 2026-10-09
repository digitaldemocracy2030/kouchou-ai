import { chartRegistry, ensurePluginsLoaded } from "@/components/charts/plugins";
import { Tooltip } from "@/components/ui/tooltip";
import type { ChartType, Result } from "@/type";
import { Button, HStack, Icon } from "@chakra-ui/react";
import { useMemo } from "react";
import { resolveChartModes } from "./SelectChartButton";

// Ensure plugins are loaded
ensurePluginsLoaded();

type Props = {
  selected: string;
  onChange: (value: string) => void;
  result: Result;
  enabledCharts?: ChartType[];
  chartOrder?: ChartType[];
  disabledModeOverrides?: Record<string, boolean>;
};

/** 散布図プラグインが扱うモードのみを返す（全体・詳細クラスタ・濃い意見） */
function isScatterMode(mode: string): boolean {
  return chartRegistry.getByMode(mode)?.manifest.id === "scatter";
}

/**
 * 全画面表示のまま、散布図のクラスタ粒度（大きいクラスタ / 細かいクラスタ）を切り替える。
 * 通常のモード選択と同じ選択状態（selectedChart）を切り替えるため、全画面を抜けずに
 * 「全体」「詳細クラスタ」「濃い意見」を行き来できる。散布図以外の表示中は何も描画しない。
 */
export function ScatterLevelSwitch({
  selected,
  onChange,
  result,
  enabledCharts,
  chartOrder,
  disabledModeOverrides = {},
}: Props) {
  const modes = useMemo(
    () =>
      resolveChartModes(result, enabledCharts, chartOrder, disabledModeOverrides).filter((m) => isScatterMode(m.id)),
    [result, enabledCharts, chartOrder, disabledModeOverrides],
  );

  if (!isScatterMode(selected) || modes.length < 2) return null;

  return (
    <HStack as="fieldset" aria-label="クラスタの粒度" gap={1} border="none" p={0} m={0} minW={0}>
      {modes.map((mode) => {
        const isSelected = mode.id === selected;
        const button = (
          <Button
            key={mode.id}
            size="sm"
            h="44px"
            px={3}
            variant={isSelected ? "solid" : "outline"}
            aria-pressed={isSelected}
            disabled={mode.isDisabled}
            onClick={() => {
              if (!isSelected) onChange(mode.id);
            }}
          >
            <Icon as={mode.icon} />
            {mode.label}
          </Button>
        );
        return mode.tooltip ? (
          <Tooltip key={mode.id} content={mode.tooltip} openDelay={0} closeDelay={0}>
            {button}
          </Tooltip>
        ) : (
          button
        );
      })}
    </HStack>
  );
}
