import { ScatterLevelSwitch } from "@/components/charts/ScatterLevelSwitch";
import { chartRegistry, ensurePluginsLoaded } from "@/components/charts/plugins";
import type { ChartRenderContext } from "@/components/charts/plugins/types";
import { FullscreenToolbar } from "@/components/report/FullscreenToolbar";
import type { ChartType, Result } from "@/type";
import { Box, Dialog, Portal } from "@chakra-ui/react";

// Ensure plugins are loaded
ensurePluginsLoaded();

type ReportProps = {
  result: Result;
  selectedChart: string;
  isFullscreen: boolean;
  onExitFullscreen: () => void;
  /** 全画面のままクラスタ粒度を切り替えるためのハンドラ（未指定なら切替UIを出さない） */
  onChangeChart?: (chart: string) => void;
  enabledCharts?: ChartType[];
  chartOrder?: ChartType[];
  disabledModeOverrides?: Record<string, boolean>;
  showClusterLabels: boolean;
  onToggleClusterLabels: (show: boolean) => void;
  showConvexHull: boolean;
  treemapLevel: string;
  onTreeZoom: (level: string) => void;
};

export function Chart({
  result,
  selectedChart,
  isFullscreen,
  onExitFullscreen,
  onChangeChart,
  enabledCharts,
  chartOrder,
  disabledModeOverrides,
  showClusterLabels,
  onToggleClusterLabels,
  showConvexHull,
  treemapLevel,
  onTreeZoom,
}: ReportProps) {
  // Create render context for plugins
  const renderContext: ChartRenderContext = {
    result,
    selectedChart,
    isFullscreen,
    filteredArgumentIds: result.filteredArgumentIds,
    showClusterLabels,
    showConvexHull,
    treemapLevel,
    onTreeZoom,
    onHover: undefined,
  };

  // Get the plugin that handles the selected chart mode
  const plugin = chartRegistry.getByMode(selectedChart);

  if (isFullscreen) {
    return (
      <Dialog.Root size="full" open={isFullscreen} onOpenChange={onExitFullscreen}>
        <Portal>
          <Dialog.Backdrop />
          <Dialog.Positioner>
            <Dialog.Content>
              <Box
                w="100%"
                h="100dvh"
                display="flex"
                flexDirection="column"
                justifyContent="center"
                alignItems="center"
                bg="#fff"
              >
                <FullscreenToolbar onExitFullscreen={onExitFullscreen}>
                  {onChangeChart && (
                    <ScatterLevelSwitch
                      selected={selectedChart}
                      onChange={onChangeChart}
                      result={result}
                      enabledCharts={enabledCharts}
                      chartOrder={chartOrder}
                      disabledModeOverrides={disabledModeOverrides}
                    />
                  )}
                </FullscreenToolbar>
                <Box w="100%" flex="1" minH={0} overflow={selectedChart === "hierarchyList" ? "auto" : "hidden"}>
                  {plugin?.render(renderContext)}
                </Box>
              </Box>
            </Dialog.Content>
          </Dialog.Positioner>
        </Portal>
      </Dialog.Root>
    );
  }

  return (
    <Box mx={"auto"} w={"100%"} maxW={"1200px"} mb={10} border={"1px solid #ccc"}>
      <Box h={selectedChart === "hierarchyList" ? "auto" : "500px"} mb={0}>
        {plugin?.render({ ...renderContext, onHover: undefined })}
      </Box>
    </Box>
  );
}
