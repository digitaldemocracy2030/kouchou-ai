/**
 * Hierarchy List Plugin
 *
 * Displays clusters as an expandable hierarchical bullet list: the "detail mode"
 * for reading everything and drilling down to each opinion (and its source link).
 * Ported from policy-pr-hub's HierarchicalBulletList (Team Mirai, 2025).
 */

import { ListViewIcon } from "@/components/icons/ViewIcons";
import { HierarchyListChart } from "../HierarchyListChart";
import type { ChartPlugin, ChartRenderContext } from "./types";

export const hierarchyListPlugin: ChartPlugin = {
  manifest: {
    id: "hierarchy-list",
    name: "階層リスト（詳細モード）",
    description: "全部読む・掘り下げるための見方。グループを展開して要約と個別の意見を順に読み、出典に辿れます",
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
        config={result.config}
        comments={result.comments}
      />
    );
  },
};
