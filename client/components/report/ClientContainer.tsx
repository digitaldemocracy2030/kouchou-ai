"use client";

import { SelectChartButton } from "@/components/charts/SelectChartButton";
import { Chart } from "@/components/report/Chart";
import { ClusterOverview } from "@/components/report/ClusterOverview";
import { DisplaySettingDialog } from "@/components/report/DisplaySettingDialog";
import type { Cluster, Result } from "@/type";
import { useEffect, useState } from "react";

type Props = {
  result: Result;
};

export function ClientContainer({ result }: Props) {
  const [filteredResult, setFilteredResult] = useState<Result>(result);
  const [openDensityFilterSetting, setOpenDensityFilterSetting] =
    useState(false);
  const [selectedChart, setSelectedChart] = useState("scatterAll");
  const [maxDensity, setMaxDensity] = useState(0.2);
  const [minValue, setMinValue] = useState(5);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [isDenseGroupEnabled, setIsDenseGroupEnabled] = useState(true);
  const [showClusterLabels, setShowClusterLabels] = useState(true);
  const [showAxisLabels, setShowAxisLabels] = useState(true);
  const [treemapLevel, setTreemapLevel] = useState("0");

  // maxDensityやminValueが変化するたびに密度フィルターの結果をチェック
  useEffect(() => {
    const { filtered, isEmpty } = getDenseClusters(
      result.clusters || [],
      maxDensity,
      minValue,
    );
    setIsDenseGroupEnabled(!isEmpty);
  }, [maxDensity, minValue, result.clusters]);

  function updateFilteredResult(maxDensity: number, minValue: number) {
    if (!result) return;
    const { filtered } = getDenseClusters(
      result.clusters || [],
      maxDensity,
      minValue,
    );
    setFilteredResult({
      ...result,
      clusters: filtered,
    });
  }

  function onChangeDensityFilter(maxDensity: number, minValue: number) {
    setMaxDensity(maxDensity);
    setMinValue(minValue);
    if (selectedChart === "scatterDensity") {
      updateFilteredResult(maxDensity, minValue);
    }
  }

  // 表示するクラスタを選択
  const clustersToDisplay = selectedChart === "scatterDensity"
    ? filteredResult.clusters.filter(c => c.level === Math.max(...filteredResult.clusters.map(c => c.level)))
    : result.clusters.filter(c => c.level === 1);

  return (
    <>
      {openDensityFilterSetting && (
        <DisplaySettingDialog
          currentMaxDensity={maxDensity}
          currentMinValue={minValue}
          onClose={() => {
            setOpenDensityFilterSetting(false);
          }}
          onChangeFilter={onChangeDensityFilter}
          showClusterLabels={showClusterLabels}
          onToggleClusterLabels={setShowClusterLabels}
          showAxisLabels={showAxisLabels}
          onToggleAxisLabels={setShowAxisLabels}
          hasAxisData={!!(filteredResult.x_axis && filteredResult.y_axis && 
            Object.keys(filteredResult.x_axis).length > 0 && 
            Object.keys(filteredResult.y_axis).length > 0)}
        />
      )}
      <SelectChartButton
        selected={selectedChart}
        onChange={(selectedChart) => {
          setSelectedChart(selectedChart);
          if (selectedChart === "scatterAll" || selectedChart === "treemap") {
            updateFilteredResult(1, 0);
          }
          if (selectedChart === "scatterDensity") {
            updateFilteredResult(maxDensity, minValue);
          }
        }}
        onClickDensitySetting={() => {
          setOpenDensityFilterSetting(true);
        }}
        onClickFullscreen={() => {
          setIsFullscreen(true);
        }}
        isDenseGroupEnabled={isDenseGroupEnabled}
      />
      <Chart
        result={filteredResult}
        selectedChart={selectedChart}
        isFullscreen={isFullscreen}
        onExitFullscreen={() => {
          setIsFullscreen(false);
        }}
        showClusterLabels={showClusterLabels}
        onToggleClusterLabels={setShowClusterLabels}
        showAxisLabels={showAxisLabels}
        onToggleAxisLabels={setShowAxisLabels}
        treemapLevel={treemapLevel}
        onTreeZoom={setTreemapLevel}
      />
      
      {/* クラスタの概要を表示 */}
      {clustersToDisplay.map((c) => (
        <ClusterOverview key={c.id} cluster={c} />
      ))}
    </>
  );
}

function getDenseClusters(
  clusters: Cluster[],
  maxDensity: number,
  minValue: number,
): { filtered: Cluster[]; isEmpty: boolean } {
  // 全意見グループの中で一番大きい level を deepestLevel として取得します。
  const deepestLevel = clusters.reduce(
    (maxLevel, cluster) => Math.max(maxLevel, cluster.level),
    0,
  );

  console.log("=== Dense Cluster Extraction ===");
  console.log(
    `Filter settings: maxDensity=${maxDensity}, minValue=${minValue}`,
  );

  const deepestLevelClusters = clusters.filter((c) => c.level === deepestLevel);
  console.log(
    `Total clusters at deepest level (${deepestLevel}): ${deepestLevelClusters.length}`,
  );

  for (const cluster of deepestLevelClusters) {
    console.log(
      `Cluster ID: ${cluster.id}, Label: ${cluster.label}, Density: ${cluster.density_rank_percentile}, Elements: ${cluster.value}`,
    );
  }

  const filteredDeepestLevelClusters = deepestLevelClusters
    .filter((c) => c.density_rank_percentile <= maxDensity)
    .filter((c) => c.value >= minValue);

  console.log(
    `Clusters after filtering: ${filteredDeepestLevelClusters.length}`,
  );
  console.log(filteredDeepestLevelClusters);
  console.log("=== End of Dense Cluster Extraction ===");

  return {
    filtered: [
      ...clusters.filter((c) => c.level !== deepestLevel),
      ...filteredDeepestLevelClusters,
    ],
    isEmpty: filteredDeepestLevelClusters.length === 0,
  };
}
