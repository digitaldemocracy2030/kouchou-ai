import { ScatterChart } from "@/components/charts/ScatterChart";
import { TreemapChart } from "@/components/charts/TreemapChart";
import { Tooltip } from "@/components/ui/tooltip";
import type { Result } from "@/type";
import { Box, Button, HStack, Icon } from "@chakra-ui/react";
import { Minimize2 } from "lucide-react";

type ReportProps = {
  result: Result;
  selectedChart: string;
  isFullscreen: boolean;
  onExitFullscreen: () => void;
  showClusterLabels: boolean;
  onToggleClusterLabels: (show: boolean) => void;
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
  treemapLevel,
  onTreeZoom,
}: ReportProps) {
  if (isFullscreen) {
    return (
      <Box
        w={"100%"}
        h={"100vh"}
        position={"fixed"}
        top={0}
        bottom={0}
        left={0}
        right={0}
        bgColor={"#fff"}
        zIndex={1000}
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
        {(selectedChart === "scatterAll" || selectedChart === "scatterDensity") && (
          <ScatterChart
            clusterList={result.clusters}
            argumentList={result.arguments}
            targetLevel={selectedChart === "scatterAll" ? 1 : Math.max(...result.clusters.map((c) => c.level))}
            onHover={() => setTimeout(avoidHoverTextCoveringShrinkButton, 500)}
            showClusterLabels={showClusterLabels}
            filteredArgumentIds={result.filteredArgumentIds}
          />
        )}
        {selectedChart === "treemap" && (
          <TreemapChart
            key={treemapLevel}
            clusterList={result.clusters}
            argumentList={result.arguments}
            onHover={avoidHoverTextCoveringShrinkButton}
            level={treemapLevel}
            onTreeZoom={onTreeZoom}
          />
        )}
      </Box>
    );
  }

  return (
    <Box mx={"auto"} w={"100%"} maxW={"1200px"} mb={10} border={"1px solid #ccc"}>
      <Box h={"500px"} mb={0}>
        {selectedChart === "treemap" && (
          <TreemapChart
            key={treemapLevel}
            clusterList={result.clusters}
            argumentList={result.arguments}
            level={treemapLevel}
            onTreeZoom={onTreeZoom}
          />
        )}
        {(selectedChart === "scatterAll" || selectedChart === "scatterDensity") && (
          <ScatterChart
            clusterList={result.clusters}
            argumentList={result.arguments}
            targetLevel={selectedChart === "scatterAll" ? 1 : Math.max(...result.clusters.map((c) => c.level))}
            showClusterLabels={showClusterLabels}
            filteredArgumentIds={result.filteredArgumentIds}
          />
        )}
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
