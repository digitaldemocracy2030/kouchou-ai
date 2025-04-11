import { ScatterChart } from "@/components/charts/ScatterChart";
import { TreemapChart } from "@/components/charts/TreemapChart";
import { Tooltip } from "@/components/ui/tooltip";
import type { Result } from "@/type";
import { Box, Button, Icon } from "@chakra-ui/react";
import { Undo2Icon } from "lucide-react";

type ReportProps = {
  result: Result;
  selectedChart: string;
  isFullscreen: boolean;
  onExitFullscreen: () => void;
};

export function Chart({
  result,
  selectedChart,
  isFullscreen,
  onExitFullscreen,
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
        <Tooltip content={"全画面終了"} openDelay={0} closeDelay={0}>
          <Button
            onClick={onExitFullscreen}
            h={"50px"}
            position={"fixed"}
            top={5}
            right={5}
            zIndex={1}
            borderWidth={2}
          >
            <Icon>
              <Undo2Icon />
            </Icon>
          </Button>
        </Tooltip>
        {(selectedChart === "scatterAll" ||
          selectedChart === "scatterDensity") && (
          <ScatterChart
            clusterList={result.clusters}
            argumentList={result.arguments}
            targetLevel={
              selectedChart === "scatterAll"
                ? 1
                : Math.max(...result.clusters.map((c) => c.level))
            }
            onHover={avoidHoverTextCoveringShrinkButton}
          />
        )}
        {selectedChart === "treemap" && (
          <TreemapChart
            clusterList={result.clusters}
            argumentList={result.arguments}
            onHover={avoidHoverTextCoveringShrinkButton}
          />
        )}
      </Box>
    );
  }

  return (
    <Box mx={"auto"} w={"100%"} maxW={"1200px"} mb={10}>
      <Box h={"500px"} mb={5}>
        {selectedChart === "treemap" && (
          <TreemapChart
            clusterList={result.clusters}
            argumentList={result.arguments}
            onHover={avoidHoverTextCoveringShrinkButton}
          />
        )}
        {(selectedChart === "scatterAll" ||
          selectedChart === "scatterDensity") && (
          <ScatterChart
            clusterList={result.clusters}
            argumentList={result.arguments}
            targetLevel={
              selectedChart === "scatterAll"
                ? 1
                : Math.max(...result.clusters.map((c) => c.level))
            }
            onHover={avoidHoverTextCoveringShrinkButton}
          />
        )}
      </Box>
    </Box>
  );
}

export function avoidHoverTextCoveringShrinkButton(): void {
  const hoverlayer = document.querySelector(".hoverlayer");
  if (!hoverlayer) return;
  const tooltipButtons =document.querySelectorAll('[type="button"][id^="tooltip:«"][id$="»:trigger"]');
  let shrinkButton = null;
  for (let tooltipButton of tooltipButtons) {
    if (tooltipButton?.computedStyleMap()?.get("z-index") == 1) {
      // 候補となるボタンが以下の3つ。
      //  - SelectChartButton >「濃い意見グループ設定」「全画面表示」
      //  - Chart >「全画面終了」
      // そのうち目当ての「全画面終了」ボタンのみプロットの全面に表示されるようにz-indexが1と指定されている。他は未指定につき"auto"となる。
      // もう少しちゃんとした判定方法があるはずだが、思いつかないので暫定的にこうする。
      shrinkButton = tooltipButton;
      break;
    }
  }
  if (!shrinkButton) return;
  const hoverPos = hoverlayer.getBoundingClientRect();
  const btnPos = shrinkButton.getBoundingClientRect();
  const isCovered = !(btnPos.top > hoverPos.bottom || btnPos.bottom < hoverPos.top || btnPos.left > hoverPos.right || btnPos.right < hoverPos.left);
  if (!isCovered) return;

  const diff = btnPos.bottom - hoverPos.top;

  const hovertext = hoverlayer.querySelector(".hovertext");
  if (!hovertext) return;
  const originalTransform = hovertext.getAttribute("transform"); // 例：translate(1643,66)
  if (!originalTransform) return;
  const newTransform = originalTransform.split(",")[0]
    + ","
    + (Number(originalTransform.split(",")[1].slice(0, -1)) + diff).toString()
    + ")";
  hovertext.setAttribute("transform", newTransform);

  const hoverpath = hovertext.querySelector("path");
  if (!hoverpath) return;
  const originalPath = hoverpath.getAttribute("d"); // 例：M0,-65 L-6,40 v89 h-201 v-190 H-6 V28 Z
  if (!originalPath) return;
  const leftOrRight = originalPath.includes("L") ? "L" : "R"; // 吹き出しが起点から左右どちらに出るか
  const newPath = originalPath.split(",")[0]
    + ","
    + (Number(originalPath.split(",")[1].split(leftOrRight)[0]) - diff).toString()
    + leftOrRight
    + originalPath.split(leftOrRight)[1];
  hoverpath.setAttribute("d", newPath);
}