import { ScatterLevelSwitch } from "@/components/charts/ScatterLevelSwitch";
import { chartRegistry, ensurePluginsLoaded } from "@/components/charts/plugins";
import type { ChartRenderContext } from "@/components/charts/plugins/types";
import { FullscreenToolbar } from "@/components/report/FullscreenToolbar";
import { LanguageToggle } from "@/components/report/LanguageToggle";
import { Switch } from "@/components/ui/switch";
import { useMessages } from "@/lib/i18n/LanguageContext";
import type { ChartType, Result } from "@/type";
import { Box, Center, Dialog, Portal } from "@chakra-ui/react";

// Ensure plugins are loaded
ensurePluginsLoaded();

type ReportProps = Pick<
  ChartRenderContext,
  | "oppositionClusterIds"
  | "oppositionClusterId"
  | "oppositionSelection"
  | "onOppositionSelectionChange"
  | "onOpenOpposition"
  | "onBackFromOpposition"
  | "reopenClusterId"
> & {
  /** 描画に使う結果（属性フィルタ・密度フィルタ適用後） */
  result: Result;
  /**
   * 全画面の粒度切替で「どのモードが選べるか」を判定するための、フィルタ適用前の結果。
   * 密度フィルタで最深 level のクラスタが全て落ちても、通常のセレクタと同じ判定になるよう result と分ける。
   * 未指定なら result を使う。
   */
  modeResult?: Result;
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
  treemapDensityEnabled?: boolean;
  onTreemapDensityChange?: (checked: boolean) => void;
  /** 散布図でクラスタが選択された時に通知する（連動文章・一覧のハイライト用） */
  onSelectCluster?: (clusterId: string) => void;
  /** テキスト検索の文字列（空 = 検索なし） */
  textSearch?: string;
};

/**
 * 選択中のモードのチャートプラグインを描画する。
 * 全画面時はダイアログで包み、上部ツールバーに「全画面終了」と（onChangeChart があれば）粒度切替を置く。
 */
export function Chart({
  result,
  modeResult,
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
  treemapDensityEnabled = false,
  onTreemapDensityChange,
  onSelectCluster,
  oppositionClusterIds,
  oppositionClusterId,
  oppositionSelection,
  onOppositionSelectionChange,
  onOpenOpposition,
  onBackFromOpposition,
  reopenClusterId,
  textSearch,
}: ReportProps) {
  const messages = useMessages();
  // Create render context for plugins
  const renderContext: ChartRenderContext = {
    result,
    modeResult,
    selectedChart,
    isFullscreen,
    filteredArgumentIds: result.filteredArgumentIds,
    textSearch,
    showClusterLabels,
    showConvexHull,
    treemapLevel,
    onTreeZoom,
    onSelectCluster,
    oppositionClusterIds,
    oppositionClusterId,
    oppositionSelection,
    onOppositionSelectionChange,
    onOpenOpposition,
    onBackFromOpposition,
    reopenClusterId,
    onHover: undefined,
  };

  // Get the plugin that handles the selected chart mode
  const plugin = chartRegistry.getByMode(selectedChart);
  const flowLayout = plugin?.manifest.modes.find((mode) => mode.id === selectedChart)?.layout === "flow";
  const treemapDensityControl = selectedChart === "treemap" && onTreemapDensityChange && (
    <Switch
      size="sm"
      flexShrink={0}
      inputProps={{ role: "switch" }}
      checked={treemapDensityEnabled}
      onCheckedChange={({ checked }) => onTreemapDensityChange(checked)}
    >
      {messages.treemapDenseOnly}
    </Switch>
  );
  const chartContent =
    selectedChart === "treemap" && treemapDensityEnabled && result.filteredArgumentIds?.length === 0 ? (
      <Center as="output" h="100%" px={4}>
        {messages.noOpinionsHere}
      </Center>
    ) : (
      plugin?.render(renderContext)
    );

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
                      result={modeResult ?? result}
                      enabledCharts={enabledCharts}
                      chartOrder={chartOrder}
                      disabledModeOverrides={disabledModeOverrides}
                    />
                  )}
                  {treemapDensityControl}
                  {/* 全画面のまま表示言語を切り替えられるようにする（通常表示の切替と状態を共有） */}
                  <LanguageToggle size="sm" />
                </FullscreenToolbar>
                <Box w="100%" flex="1" minH={0} overflow={flowLayout ? "auto" : "hidden"}>
                  {chartContent}
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
      {treemapDensityControl && (
        <Box px={3} py={2} borderBottomWidth="1px">
          {treemapDensityControl}
        </Box>
      )}
      <Box h={flowLayout ? "auto" : "500px"} mb={0}>
        {chartContent}
      </Box>
    </Box>
  );
}
