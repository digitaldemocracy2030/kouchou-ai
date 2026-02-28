"use client";

import { DEFAULT_ENABLED_CHARTS, SelectChartButton } from "@/components/charts/SelectChartButton";
import {
  chartRegistry,
  ensurePluginsLoaded,
  formatValidationResult,
  validateResultData,
  validateVisualizationConfig,
} from "@/components/charts/plugins";
import { AttributeFilterDialog } from "@/components/report/AttributeFilterDialog";
import { Chart } from "@/components/report/Chart";
import { ClusterOverview } from "@/components/report/ClusterOverview";
import { DisplaySettingDialog } from "@/components/report/DisplaySettingDialog";
import type { Cluster, Result } from "@/type";
import { useEffect, useMemo, useState } from "react";
import {
  type AttributeFilters,
  type FilterParams,
  type NumericRangeFilters,
  computeAttributeMetas,
  countActiveFilters,
  filterArgumentIds,
  hasActiveFilters,
} from "./attributeFilterUtils";

// Ensure plugins are loaded for validation
ensurePluginsLoaded();

type Props = {
  result: Result;
};

export function ClientContainer({ result }: Props) {
  // --- Validate data at load time ---
  useEffect(() => {
    const resultValidation = validateResultData(result);
    if (!resultValidation.valid || resultValidation.warnings.length > 0) {
      console.warn(`Result data validation:\n${formatValidationResult(resultValidation)}`);
    }
    const configValidation = validateVisualizationConfig(result.visualizationConfig, chartRegistry);
    if (!configValidation.valid || configValidation.warnings.length > 0) {
      console.warn(`Visualization config validation:\n${formatValidationResult(configValidation)}`);
    }
  }, [result]);

  // --- Extract visualization config with defaults ---
  const visualizationConfig = result.visualizationConfig;
  const enabledCharts = visualizationConfig?.enabledCharts ?? DEFAULT_ENABLED_CHARTS;
  const chartOrder = visualizationConfig?.chartOrder;
  const defaultChart = visualizationConfig?.defaultChart ?? enabledCharts[0] ?? "scatterAll";
  const defaultParams = visualizationConfig?.params;

  // --- UI State ---
  const [openDensityFilterSetting, setOpenDensityFilterSetting] = useState(false);
  const [selectedChart, setSelectedChart] = useState<string>(defaultChart);
  const [maxDensity, setMaxDensity] = useState(defaultParams?.scatterDensity?.maxDensity ?? 0.2);
  const [minValue, setMinValue] = useState(defaultParams?.scatterDensity?.minValue ?? 5);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [showClusterLabels, setShowClusterLabels] = useState(defaultParams?.showClusterLabels ?? true);
  const [showConvexHull, setShowConvexHull] = useState(true);
  const [treemapLevel, setTreemapLevel] = useState("0");

  // --- 属性メタデータ（純粋な派生データなのでuseMemoで計算） ---
  const attributeMetas = useMemo(() => computeAttributeMetas(result.arguments), [result.arguments]);

  // --- 属性フィルター状態 ---
  const [attributeFilters, setAttributeFilters] = useState<AttributeFilters>({});
  const [numericRanges, setNumericRanges] = useState<NumericRangeFilters>({});
  const [enabledRanges, setEnabledRanges] = useState<Record<string, boolean>>({});
  const [includeEmptyValues, setIncludeEmptyValues] = useState<Record<string, boolean>>({});
  const [textSearch, setTextSearch] = useState<string>("");
  const [openAttributeFilter, setOpenAttributeFilter] = useState(false);

  // --- フィルタパラメータを一つのオブジェクトにまとめる ---
  const filterParams: FilterParams = useMemo(
    () => ({ attributeFilters, numericRanges, enabledRanges, includeEmptyValues, textSearch }),
    [attributeFilters, numericRanges, enabledRanges, includeEmptyValues, textSearch],
  );

  // --- 密度フィルタの有効性（派生データ） ---
  const isDenseGroupEnabled = useMemo(() => {
    const { isEmpty } = getDenseClusters(result.clusters || [], maxDensity, minValue);
    return !isEmpty;
  }, [result.clusters, maxDensity, minValue]);

  // --- フィルタ済み結果を派生計算（stale closure問題を解消） ---
  const filteredResult = useMemo(() => {
    // 1. 属性・テキストフィルタの適用
    const filteredArgIds = filterArgumentIds(result.arguments, filterParams);

    // 2. 密度フィルタの適用（scatterDensityモードのみ有効）
    const effectiveMaxDensity = selectedChart === "scatterDensity" ? maxDensity : 1;
    const effectiveMinValue = selectedChart === "scatterDensity" ? minValue : 0;
    const { filtered: densityFilteredClusters } = getDenseClusters(
      result.clusters || [],
      effectiveMaxDensity,
      effectiveMinValue,
    );

    // 3. フィルタ条件に合致する引数がないクラスタをマーク
    let combinedClusters = densityFilteredClusters;
    if (filteredArgIds) {
      const filteredArgIdSet = new Set(filteredArgIds);
      const clusterIdsWithFilteredArgs = new Set<string>();
      for (const arg of result.arguments) {
        if (filteredArgIdSet.has(arg.arg_id)) {
          for (const clusterId of arg.cluster_ids) {
            clusterIdsWithFilteredArgs.add(clusterId);
          }
        }
      }
      combinedClusters = densityFilteredClusters.map((cluster) =>
        clusterIdsWithFilteredArgs.has(cluster.id) ? cluster : { ...cluster, allFiltered: true },
      );
    }

    return {
      ...result,
      clusters: combinedClusters,
      filteredArgumentIds: filteredArgIds,
    };
  }, [result, filterParams, selectedChart, maxDensity, minValue]);

  // --- UIハンドラ群 ---
  const handleApplyAttributeFilters = (
    filters: AttributeFilters,
    numericRanges_: NumericRangeFilters,
    includeEmpty: Record<string, boolean>,
    enabledRanges_: Record<string, boolean>,
    textSearchString: string,
  ) => {
    setAttributeFilters(filters);
    setNumericRanges(numericRanges_);
    setIncludeEmptyValues(includeEmpty);
    setEnabledRanges(enabledRanges_);
    setTextSearch(textSearchString);
  };

  const onChangeDensityFilter = (density: number, value: number) => {
    setMaxDensity(density);
    setMinValue(value);
  };

  // --- クラスタ表示 ---
  const clustersToDisplay = useMemo(() => {
    let c: Cluster[] = [];
    if (selectedChart === "scatterDensity" || selectedChart === "scatterDetail") {
      const max = Math.max(...filteredResult.clusters.map((c) => c.level));
      c = filteredResult.clusters.filter((c) => c.level === max);
    } else {
      c = result.clusters.filter((c) => c.level === 1);
    }
    return c.sort((a, b) => b.value - a.value);
  }, [result.clusters, filteredResult.clusters, selectedChart]);

  // --- UI ---
  return (
    <div>
      {openDensityFilterSetting && (
        <DisplaySettingDialog
          currentMaxDensity={maxDensity}
          currentMinValue={minValue}
          onClose={() => setOpenDensityFilterSetting(false)}
          onChangeFilter={onChangeDensityFilter}
          showClusterLabels={showClusterLabels}
          onToggleClusterLabels={setShowClusterLabels}
          showConvexHull={showConvexHull}
          onToggleConvexHull={setShowConvexHull}
        />
      )}
      {openAttributeFilter && (
        <AttributeFilterDialog
          onClose={() => setOpenAttributeFilter(false)}
          onApplyFilters={handleApplyAttributeFilters}
          attributes={attributeMetas}
          initialFilters={attributeFilters}
          initialNumericRanges={numericRanges}
          initialEnabledRanges={enabledRanges}
          initialIncludeEmptyValues={includeEmptyValues}
          initialTextSearch={textSearch}
        />
      )}
      <SelectChartButton
        selected={selectedChart}
        onChange={setSelectedChart}
        onClickDensitySetting={() => setOpenDensityFilterSetting(true)}
        onClickFullscreen={() => setIsFullscreen(true)}
        result={result}
        disabledModeOverrides={{ scatterDensity: !isDenseGroupEnabled }}
        enabledCharts={enabledCharts}
        chartOrder={chartOrder}
        onClickAttentionFilter={() => setOpenAttributeFilter(true)}
        isAttentionFilterEnabled={attributeMetas.length > 0}
        showAttentionFilterBadge={hasActiveFilters(filterParams)}
        attentionFilterBadgeCount={countActiveFilters(filterParams)}
      />
      <Chart
        result={filteredResult}
        selectedChart={selectedChart}
        isFullscreen={isFullscreen}
        onExitFullscreen={() => setIsFullscreen(false)}
        showClusterLabels={showClusterLabels}
        onToggleClusterLabels={setShowClusterLabels}
        showConvexHull={showConvexHull}
        treemapLevel={treemapLevel}
        onTreeZoom={setTreemapLevel}
      />
      {clustersToDisplay.map((c) => (
        <ClusterOverview key={c.id} cluster={c} />
      ))}
    </div>
  );
}

function getDenseClusters(
  clusters: Cluster[],
  maxDensity: number,
  minValue: number,
): { filtered: Cluster[]; isEmpty: boolean } {
  const deepestLevel = clusters.reduce((maxLevel, cluster) => Math.max(maxLevel, cluster.level), 0);
  const deepestLevelClusters = clusters.filter((c) => c.level === deepestLevel);
  const filteredDeepestLevelClusters = deepestLevelClusters
    .filter((c) => c.density_rank_percentile <= maxDensity)
    .filter((c) => c.value >= minValue);
  return {
    filtered: [...clusters.filter((c) => c.level !== deepestLevel), ...filteredDeepestLevelClusters],
    isEmpty: filteredDeepestLevelClusters.length === 0,
  };
}
