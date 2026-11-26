"use client";

import { DEFAULT_ENABLED_CHARTS, SelectChartButton, resolveChartModes } from "@/components/charts/SelectChartButton";
import {
  chartRegistry,
  ensurePluginsLoaded,
  formatValidationResult,
  validateResultData,
  validateVisualizationConfig,
} from "@/components/charts/plugins";
import { OPPOSITION_CHART, getOppositionAxes } from "@/components/charts/plugins/opposition-data";
import { resolveChartSelection } from "@/components/charts/plugins/selection";
import type { OppositionSelection } from "@/components/charts/plugins/types";
import { AttributeFilterDialog } from "@/components/report/AttributeFilterDialog";
import { Chart } from "@/components/report/Chart";
import { ClusterOverview } from "@/components/report/ClusterOverview";
import { DisplaySettingDialog } from "@/components/report/DisplaySettingDialog";
import { useMessages } from "@/lib/i18n/LanguageContext";
import type { Cluster, Result } from "@/type";
import { useCallback, useEffect, useMemo, useState } from "react";
import { TreemapDetails } from "./TreemapDetails";
import {
  type AttributeFilters,
  type FilterParams,
  type NumericRangeFilters,
  computeAttributeMetas,
  countActiveFilters,
  filterArgumentIds,
  hasActiveFilters,
} from "./attributeFilterUtils";
import { applyTreemapDensityFilter, resolveFilteredTreemapLevel } from "./treemapContext";

// Ensure plugins are loaded for validation
ensurePluginsLoaded();

const DEFAULT_READING_CHARTS = [...DEFAULT_ENABLED_CHARTS, "hierarchyList"];
const NARROW_SCREEN_QUERY = "(max-width: 600px)";
const READING_CHARTS_WITH_OPPOSITION = [...DEFAULT_READING_CHARTS, OPPOSITION_CHART];

type Props = {
  result: Result;
};

export function ClientContainer({ result }: Props) {
  const messages = useMessages();

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
  const oppositionClusterIds = useMemo(
    () => new Set(getOppositionAxes(result).map((axis) => axis.cluster_id)),
    [result],
  );
  const configuredCharts = visualizationConfig?.enabledCharts;
  const enabledCharts = useMemo(() => {
    if (oppositionClusterIds.size > 0) return configuredCharts ?? READING_CHARTS_WITH_OPPOSITION;
    return configuredCharts?.filter((chart) => chart !== OPPOSITION_CHART) ?? DEFAULT_READING_CHARTS;
  }, [oppositionClusterIds, configuredCharts]);
  const canOpenOpposition = enabledCharts.includes(OPPOSITION_CHART);
  const chartOrder = visualizationConfig?.chartOrder;
  const configuredDefault = visualizationConfig?.defaultChart;
  const defaultChart =
    (configuredDefault === OPPOSITION_CHART && !canOpenOpposition ? undefined : configuredDefault) ??
    enabledCharts[0] ??
    "scatterAll";
  const defaultParams = visualizationConfig?.params;

  // --- UI State ---
  const [openDensityFilterSetting, setOpenDensityFilterSetting] = useState(false);
  const [chartPreference, setChartPreference] = useState<string>();
  const [maxDensity, setMaxDensity] = useState(defaultParams?.scatterDensity?.maxDensity ?? 0.2);
  const [minValue, setMinValue] = useState(defaultParams?.scatterDensity?.minValue ?? 5);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [narrowScreenOnMount, setNarrowScreenOnMount] = useState(false);
  const [clusterLabelPreference, setClusterLabelPreference] = useState<boolean>();
  useEffect(() => {
    setNarrowScreenOnMount(window.matchMedia(NARROW_SCREEN_QUERY).matches);
  }, []);
  const showClusterLabels = clusterLabelPreference ?? defaultParams?.showClusterLabels ?? !narrowScreenOnMount;
  const [showConvexHull, setShowConvexHull] = useState(true);
  const [treemapLevel, setTreemapLevel] = useState("0");
  const [treemapDensityEnabled, setTreemapDensityEnabled] = useState(false);
  // 散布図でクリックされたクラスタ（連動文章・一覧のハイライト対象）
  const [selectedClusterId, setSelectedClusterId] = useState<string | null>(null);
  const [oppositionOrigin, setOppositionOrigin] = useState<{ chart: string; clusterId: string }>();
  const [oppositionSelection, setOppositionSelection] = useState<OppositionSelection>({});
  const [reopenClusterId, setReopenClusterId] = useState<string>();

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

  const { filtered: densityFilteredClusters, isEmpty: isDenseGroupEmpty } = useMemo(
    () => getDenseClusters(result.clusters || [], maxDensity, minValue),
    [result.clusters, maxDensity, minValue],
  );
  const isDenseGroupEnabled = !isDenseGroupEmpty;

  const disabledModeOverrides = useMemo(() => ({ scatterDensity: !isDenseGroupEnabled }), [isDenseGroupEnabled]);
  const modes = useMemo(
    () => resolveChartModes(result, enabledCharts, chartOrder, disabledModeOverrides),
    [result, enabledCharts, chartOrder, disabledModeOverrides],
  );
  const requestedChart = chartPreference ?? defaultChart;
  const selectedChart = resolveChartSelection(
    modes,
    requestedChart,
    requestedChart === "scatterDensity" ? "scatterAll" : undefined,
  );

  useEffect(() => {
    // 初回は初期表示の指定がない場合に限り、狭い画面で階層リストを優先する。
    if (
      chartPreference === undefined &&
      !visualizationConfig?.defaultChart &&
      resolveChartSelection(modes, "hierarchyList") === "hierarchyList" &&
      window.matchMedia(NARROW_SCREEN_QUERY).matches
    ) {
      setChartPreference("hierarchyList");
    } else if (selectedChart && selectedChart !== chartPreference) {
      // 条件を戻しても、フォールバック前のモードへ勝手に戻さない。
      setChartPreference(selectedChart);
      setSelectedClusterId(null);
    }
  }, [chartPreference, modes, selectedChart, visualizationConfig?.defaultChart]);

  // 表示モードを変えたら、散布図で選んだクラスタの選択と対立軸ビューの戻り先も解除する。
  const changeChart = useCallback(
    (chart: string) => {
      if (resolveChartSelection(modes, chart) !== chart) return;
      setChartPreference(chart);
      setSelectedClusterId(null);
      setOppositionOrigin(undefined);
      setOppositionSelection({});
      setReopenClusterId(undefined);
    },
    [modes],
  );

  const openOpposition = useCallback(
    (clusterId: string) => {
      if (!selectedChart || resolveChartSelection(modes, OPPOSITION_CHART) !== OPPOSITION_CHART) return;
      setOppositionOrigin({ chart: selectedChart, clusterId });
      setOppositionSelection({ clusterId });
      setChartPreference(OPPOSITION_CHART);
    },
    [modes, selectedChart],
  );

  const backFromOpposition = useCallback(() => {
    if (!oppositionOrigin) return;
    setChartPreference(oppositionOrigin.chart);
    setSelectedClusterId(oppositionOrigin.clusterId);
    setReopenClusterId(oppositionOrigin.clusterId);
    setOppositionOrigin(undefined);
  }, [oppositionOrigin]);

  // --- 属性・テキストフィルタの適用（密度変更時に再計算しないよう分離） ---
  const filteredArgIds = useMemo(
    () => filterArgumentIds(result.arguments, filterParams),
    [result.arguments, filterParams],
  );

  // --- フィルタ適用中か（undefined = フィルタなし） ---
  const isFiltering = filteredArgIds !== undefined;

  // --- 各クラスタのフィルタ後件数（treemapContext と同じ数え方で、散布図一覧の件数表示に使う） ---
  const clusterCounts = useMemo(() => {
    const counts = new Map<string, number>();
    const allowed = filteredArgIds ? new Set(filteredArgIds) : null;
    for (const arg of result.arguments) {
      if (allowed && !allowed.has(arg.arg_id)) continue;
      for (const id of arg.cluster_ids) counts.set(id, (counts.get(id) ?? 0) + 1);
    }
    return counts;
  }, [result.arguments, filteredArgIds]);

  // フィルタで一覧から一時的に消えた selectedClusterId は、下の map で一致せずハイライトが外れる
  // （表示モードの切り替えでは changeChart で選択自体を解除する）。

  // --- フィルタ済み結果を派生計算（stale closure問題を解消） ---
  const filteredResult = useMemo(() => {
    if (selectedChart === "treemap") {
      return treemapDensityEnabled
        ? applyTreemapDensityFilter(result, densityFilteredClusters, filteredArgIds)
        : { ...result, filteredArgumentIds: filteredArgIds };
    }

    let combinedClusters =
      selectedChart === "scatterDensity"
        ? densityFilteredClusters
        : getDenseClusters(result.clusters || [], 1, 0).filtered;
    // フィルタ条件に合致する引数がないクラスタをマーク
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
      combinedClusters = combinedClusters.map((cluster) =>
        clusterIdsWithFilteredArgs.has(cluster.id) ? cluster : { ...cluster, allFiltered: true },
      );
    }

    return {
      ...result,
      clusters: combinedClusters,
      filteredArgumentIds: filteredArgIds,
    };
  }, [result, filteredArgIds, selectedChart, densityFilteredClusters, treemapDensityEnabled]);

  const visibleTreemapLevel = useMemo(
    () =>
      selectedChart === "treemap" && treemapDensityEnabled
        ? resolveFilteredTreemapLevel(treemapLevel, result, filteredResult)
        : treemapLevel,
    [selectedChart, treemapDensityEnabled, treemapLevel, result, filteredResult],
  );
  useEffect(() => {
    if (visibleTreemapLevel !== treemapLevel) setTreemapLevel(visibleTreemapLevel);
  }, [treemapLevel, visibleTreemapLevel]);

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
    if (selectedChart === undefined || selectedChart === "hierarchyList" || selectedChart === OPPOSITION_CHART)
      return [];
    let c: Cluster[] = [];
    if (selectedChart === "scatterDensity" || selectedChart === "scatterDetail") {
      // 最深階層はフィルタ前の result で決める（抽出が 0 件でも一つ上の階層に繰り上げない）
      const max = Math.max(...result.clusters.map((c) => c.level));
      c = filteredResult.clusters.filter((c) => c.level === max);
    } else {
      c = result.clusters.filter((c) => c.level === 1);
    }
    return c.sort((a, b) => b.value - a.value);
  }, [result.clusters, filteredResult.clusters, selectedChart]);

  // 一覧の見出しから、そのクラスタを開いた階層表示へ移る。全カードで同じ関数を渡し、ClusterOverview の memo を効かせる
  const navigateToTreemap = useCallback(
    (clusterId: string) => {
      setTreemapLevel(clusterId);
      changeChart("treemap");
    },
    [changeChart],
  );
  const canNavigateToTreemap = resolveChartSelection(modes, "treemap") === "treemap";

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
          onToggleClusterLabels={setClusterLabelPreference}
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
        onChange={changeChart}
        onClickDensitySetting={() => setOpenDensityFilterSetting(true)}
        onClickFullscreen={selectedChart === undefined ? undefined : () => setIsFullscreen(true)}
        result={result}
        disabledModeOverrides={disabledModeOverrides}
        enabledCharts={enabledCharts}
        chartOrder={chartOrder}
        onClickAttentionFilter={() => setOpenAttributeFilter(true)}
        showAttentionFilterBadge={hasActiveFilters(filterParams)}
        attentionFilterBadgeCount={countActiveFilters(filterParams)}
      />
      <div id="report-chart" />
      {selectedChart === undefined ? (
        <output>{messages.noAvailableChart}</output>
      ) : (
        <Chart
          result={filteredResult}
          modeResult={result}
          selectedChart={selectedChart}
          isFullscreen={isFullscreen}
          onExitFullscreen={() => setIsFullscreen(false)}
          onChangeChart={changeChart}
          enabledCharts={enabledCharts}
          chartOrder={chartOrder}
          disabledModeOverrides={disabledModeOverrides}
          showClusterLabels={showClusterLabels}
          onToggleClusterLabels={setClusterLabelPreference}
          showConvexHull={showConvexHull}
          treemapLevel={visibleTreemapLevel}
          onTreeZoom={setTreemapLevel}
          treemapDensityEnabled={treemapDensityEnabled}
          onTreemapDensityChange={setTreemapDensityEnabled}
          onSelectCluster={setSelectedClusterId}
          oppositionClusterIds={oppositionClusterIds}
          oppositionClusterId={oppositionOrigin?.clusterId}
          oppositionSelection={oppositionSelection}
          onOppositionSelectionChange={setOppositionSelection}
          onOpenOpposition={canOpenOpposition ? openOpposition : undefined}
          onBackFromOpposition={oppositionOrigin ? backFromOpposition : undefined}
          reopenClusterId={reopenClusterId}
          textSearch={textSearch}
        />
      )}
      {selectedChart === "treemap" ? (
        <TreemapDetails
          clusters={filteredResult.clusters}
          arguments={filteredResult.arguments}
          level={visibleTreemapLevel}
          filteredIds={filteredResult.filteredArgumentIds}
          onOpenOpposition={
            canOpenOpposition && oppositionClusterIds.has(visibleTreemapLevel) ? openOpposition : undefined
          }
          onNavigate={(id) => {
            setTreemapLevel(id);
            document.getElementById("report-chart")?.scrollIntoView();
          }}
          comments={result.comments}
          showOriginalComments={result.config?.enable_original_comments}
        />
      ) : (
        clustersToDisplay.map((c) => (
          <ClusterOverview
            key={c.id}
            cluster={c}
            count={isFiltering ? (clusterCounts.get(c.id) ?? 0) : undefined}
            isFiltering={isFiltering}
            isSelected={c.id === selectedClusterId}
            onNavigate={canNavigateToTreemap ? navigateToTreemap : undefined}
            onOpenOpposition={canOpenOpposition && oppositionClusterIds.has(c.id) ? openOpposition : undefined}
          />
        ))
      )}
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
