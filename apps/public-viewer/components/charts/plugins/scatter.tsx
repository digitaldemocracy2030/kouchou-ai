/**
 * Scatter Chart Plugin
 *
 * Handles "scatterAll", "scatterDetail", and "scatterDensity" visualization modes.
 */

import { AllViewIcon, DenseViewIcon, DetailViewIcon } from "@/components/icons/ViewIcons";
import { ScatterChart } from "../ScatterChart";
import type { ChartPlugin, ChartRenderContext } from "./types";

export const scatterPlugin: ChartPlugin = {
  manifest: {
    id: "scatter",
    name: "散布図",
    description: "意見の分布を2次元で表示します",
    version: "1.0.0",
    icon: AllViewIcon,
    modes: [
      {
        id: "scatterAll",
        label: "全体",
        icon: AllViewIcon,
      },
      {
        id: "scatterDetail",
        label: "詳細クラスタ",
        icon: DetailViewIcon,
        canBeDisabled: true,
        isDisabled: (result) => {
          const maxLevel = Math.max(...result.clusters.map((c) => c.level));
          return maxLevel <= 1;
        },
        disabledTooltip: "クラスタが1階層のみのため利用できません",
      },
      {
        id: "scatterDensity",
        label: "濃い意見",
        icon: DenseViewIcon,
        canBeDisabled: true,
        isDisabled: (result) => {
          // Check if dense view is available based on cluster data
          const maxLevel = Math.max(...result.clusters.map((c) => c.level));
          // Dense view requires level > 1
          return maxLevel <= 1;
        },
        disabledTooltip: "この設定条件では抽出できませんでした",
      },
    ],
  },

  canHandle: (mode: string) => {
    return mode === "scatterAll" || mode === "scatterDetail" || mode === "scatterDensity";
  },

  render: (context: ChartRenderContext) => {
    const { result, selectedChart, filteredArgumentIds, showClusterLabels, onHover } = context;

    // Calculate target level based on mode
    // scatterAll: top-level clusters (level 1)
    // scatterDetail / scatterDensity: deepest-level clusters
    const targetLevel = selectedChart === "scatterAll" ? 1 : Math.max(...result.clusters.map((c) => c.level));

    return (
      <ScatterChart
        clusterList={result.clusters}
        argumentList={result.arguments}
        targetLevel={targetLevel}
        onHover={onHover}
        showClusterLabels={showClusterLabels}
        filteredArgumentIds={filteredArgumentIds}
        config={result.config}
      />
    );
  },
};
