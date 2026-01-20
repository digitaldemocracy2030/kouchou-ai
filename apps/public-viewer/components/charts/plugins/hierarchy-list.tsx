/**
 * Hierarchy List Plugin
 *
 * Displays clusters as an expandable hierarchical bullet list.
 * Sample plugin demonstrating the visualization plugin system.
 */

import { ListViewIcon } from "@/components/icons/ViewIcons";
import { HierarchyListChart } from "../HierarchyListChart";
import type { ChartPlugin, ChartRenderContext } from "./types";

export const hierarchyListPlugin: ChartPlugin = {
  manifest: {
    id: "hierarchy-list",
    name: "階層リスト",
    description: "クラスタを展開可能な階層リストで表示します",
    version: "1.0.0",
    icon: ListViewIcon,
    modes: [
      {
        id: "hierarchyList",
        label: "リスト",
        icon: ListViewIcon,
      },
    ],
  },

  canHandle: (mode: string) => {
    return mode === "hierarchyList";
  },

  render: (context: ChartRenderContext) => {
    const { result, filteredArgumentIds, onHover } = context;

    return (
      <HierarchyListChart
        clusterList={result.clusters}
        argumentList={result.arguments}
        onHover={onHover}
        filteredArgumentIds={filteredArgumentIds}
      />
    );
  },
};
