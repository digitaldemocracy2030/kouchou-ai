import { chartRegistry, ensurePluginsLoaded } from "@/components/charts/plugins";
import type { ChartRenderContext } from "@/components/charts/plugins/types";
import { Tooltip } from "@/components/ui/tooltip";
import type { Result } from "@/type";
import { Box, Button, Dialog, HStack, Icon, Portal } from "@chakra-ui/react";
import { Minimize2 } from "lucide-react";

// Ensure plugins are loaded
ensurePluginsLoaded();

type ReportProps = {
  result: Result;
  selectedChart: string;
  isFullscreen: boolean;
  onExitFullscreen: () => void;
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
                <HStack id="fullScreenButtons" w="100%" justifyContent="flex-end" p={2} flexShrink={0}>
                  <Tooltip content={"全画面終了"} openDelay={0} closeDelay={0}>
                    <Button aria-label="全画面終了" onClick={onExitFullscreen} h="44px" borderWidth={2}>
                      <Icon>
                        <Minimize2 />
                      </Icon>
                    </Button>
                  </Tooltip>
                </HStack>
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
