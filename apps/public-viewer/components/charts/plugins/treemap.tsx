/**
 * Treemap Chart Plugin
 *
 * Hierarchical treemap visualization for cluster structure.
 */

import { HierarchyViewIcon } from "@/components/icons/ViewIcons";
import { TreemapChart } from "../TreemapChart";
import type { ChartPlugin, ChartRenderContext } from "./types";

export const treemapPlugin: ChartPlugin = {
  manifest: {
    id: "treemap",
    name: "ツリーマップ",
    description: "階層構造をツリーマップで表示します",
    version: "1.0.0",
    icon: HierarchyViewIcon,
    modes: [
      {
        id: "treemap",
        label: "階層",
        icon: HierarchyViewIcon,
      },
    ],
  },

  canHandle: (mode: string) => {
    return mode === "treemap";
  },

  render: (context: ChartRenderContext) => {
    const { result, filteredArgumentIds, treemapLevel = "0", onTreeZoom, onHover } = context;

    return (
      <TreemapChart
        key={treemapLevel}
        clusterList={result.clusters}
        argumentList={result.arguments}
        onHover={onHover}
        level={treemapLevel}
        onTreeZoom={onTreeZoom || (() => {})}
        filteredArgumentIds={filteredArgumentIds}
      />
    );
  },
};
