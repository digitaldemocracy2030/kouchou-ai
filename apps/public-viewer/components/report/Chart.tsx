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
    onHover: isFullscreen ? () => setTimeout(avoidHoverTextCoveringShrinkButton, 500) : undefined,
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
                h="100vh"
                display="flex"
                flexDirection="column"
                justifyContent="center"
                alignItems="center"
                bg="#fff"
              >
                <HStack id={"fullScreenButtons"} position={"fixed"} top={5} right={5} zIndex={1}>
                  <Tooltip content={"全画面終了"} openDelay={0} closeDelay={0}>
                    <Button onClick={onExitFullscreen} h={"50px"} borderWidth={2}>
                      <Icon>
                        <Minimize2 />
                      </Icon>
                    </Button>
                  </Tooltip>
                </HStack>
                {plugin?.render(renderContext)}
              </Box>
            </Dialog.Content>
          </Dialog.Positioner>
        </Portal>
      </Dialog.Root>
    );
  }

  return (
    <Box mx={"auto"} w={"100%"} maxW={"1200px"} mb={10} border={"1px solid #ccc"}>
      <Box h={"500px"} mb={0}>
        {plugin?.render({ ...renderContext, onHover: undefined })}
      </Box>
    </Box>
  );
}

/**
 * If hover text is covered by 全画面終了 button, move hover text downwards until whole text is visible.
 */
function avoidHoverTextCoveringShrinkButton(): void {
  const hoverlayer = document.querySelector(".hoverlayer");
  const shrinkButton = document.getElementById("fullScreenButtons");
  if (!hoverlayer || !shrinkButton) return;
  const hoverPos = hoverlayer.getBoundingClientRect();
  const btnPos = shrinkButton.getBoundingClientRect();
  const isCovered = !(
    btnPos.top > hoverPos.bottom ||
    btnPos.bottom < hoverPos.top ||
    btnPos.left > hoverPos.right ||
    btnPos.right < hoverPos.left
  );
  if (!isCovered) return;

  const diff = btnPos.bottom - hoverPos.top;

  // move hoverlayer downwards
  const hovertext = hoverlayer.querySelector(".hovertext");
  if (!hovertext) return;
  const originalTransform = hovertext.getAttribute("transform"); // example：translate(1643,66)
  if (!originalTransform) return;
  const newTransform = `${originalTransform.split(",")[0]},${(Number(originalTransform.split(",")[1].slice(0, -1)) + diff).toString()})`;
  hovertext.setAttribute("transform", newTransform);

  // hoverpath SVGs follow either of the following patterns:
  // - bubble:    M0,-65 L-6,40 v89 h-201 v-190 H-6 V28 Z
  // - rectangle: M-160,-17 h328 v35 h-328 Z
  // In case of bubble pattern, the first point must go back to its original position.
  const hoverpath = hovertext.querySelector("path");
  if (!hoverpath) return;
  const originalPath = hoverpath.getAttribute("d");
  if (!originalPath) return;
  const bubblePointers = originalPath.match(/[Ll]/g);
  if (!bubblePointers) return; // rectangle pattern
  const bubblePointer = bubblePointers[0];
  const newPath = `${originalPath.split(",")[0]},${(Number(originalPath.split(",")[1].split(bubblePointer)[0]) - diff).toString()}${bubblePointer}${originalPath.split(bubblePointer)[1]}`;
  hoverpath.setAttribute("d", newPath);
}
