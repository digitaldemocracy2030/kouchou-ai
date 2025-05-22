"use client";

import { SelectChartButton } from "@/components/charts/SelectChartButton";
import { AttributeFilterDialog, type AttributeFilters } from "@/components/report/AttributeFilterDialog";
import { Chart } from "@/components/report/Chart";
import { ClusterOverview } from "@/components/report/ClusterOverview";
import { DisplaySettingDialog } from "@/components/report/DisplaySettingDialog";
import type { Cluster, Result } from "@/type";
import { useEffect, useMemo, useState } from "react";
import type { AttributeMeta } from "./AttributeFilterDialog";
import { type NumericRangeFilters, filterSamples } from "./attributeFilterUtils";

type Props = {
  result: Result;
};

export function ClientContainer({ result }: Props) {
  // --- UI State ---
  const [filteredResult, setFilteredResult] = useState<Result>(result);
  const [openDensityFilterSetting, setOpenDensityFilterSetting] = useState(false);
  const [selectedChart, setSelectedChart] = useState("scatterAll");
  const [maxDensity, setMaxDensity] = useState(0.2);
  const [minValue, setMinValue] = useState(5);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [isDenseGroupEnabled, setIsDenseGroupEnabled] = useState(true);
  const [showClusterLabels, setShowClusterLabels] = useState(true);
  const [treemapLevel, setTreemapLevel] = useState("0");

  // --- 標本データ生成 ---
  const samples = useMemo(() => {
    return result.arguments.map((arg) => {
      if (arg.attributes) {
        const rec: Record<string, string> = {};
        for (const [k, v] of Object.entries(arg.attributes)) {
          rec[k] = v == null ? "" : String(v);
        }
        return rec;
      }
      return {};
    });
  }, [result]);

  // --- 属性メタデータ計算（初回のみ） ---
  const [attributeMetas, setAttributeMetas] = useState<AttributeMeta[]>([]);
  useEffect(() => {
    if (!samples || samples.length === 0) {
      setAttributeMetas([]);
      return;
    }
    const attrMap: Record<string, {
      valueSet: Set<string>;
      valueCounts: Map<string, number>;
      isNumeric: boolean;
      min?: number;
      max?: number;
    }> = {};
    for (const sample of samples) {
      for (const [name, rawValue] of Object.entries(sample)) {
        const value = typeof rawValue === "string" ? rawValue : String(rawValue ?? "");
        if (!attrMap[name]) {
          attrMap[name] = {
            valueSet: new Set(),
            valueCounts: new Map(),
            isNumeric: true,
          };
        }
        attrMap[name].valueSet.add(value);
        attrMap[name].valueCounts.set(value, (attrMap[name].valueCounts.get(value) ?? 0) + 1);
        if (value.trim() !== "") {
          const num = Number(value);
          if (Number.isNaN(num)) {
            attrMap[name].isNumeric = false;
          } else if (attrMap[name].isNumeric) {
            if (attrMap[name].min === undefined || num < attrMap[name].min) attrMap[name].min = num;
            if (attrMap[name].max === undefined || num > attrMap[name].max) attrMap[name].max = num;
          }
        }
      }
    }
    const result: AttributeMeta[] = Object.entries(attrMap).map(([name, info]) => {
      const values = Array.from(info.valueSet).filter((v) => v !== "").sort();
      const valueCounts: Record<string, number> = {};
      for (const v of values) valueCounts[v] = info.valueCounts.get(v) ?? 0;
      let numericRange: [number, number] | undefined = undefined;
      if (info.isNumeric && values.length > 0 && info.min !== undefined && info.max !== undefined) {
        numericRange = [info.min, info.max];
      }
      return {
        name,
        type: info.isNumeric ? "numeric" : "categorical",
        values,
        valueCounts,
        numericRange,
      };
    });
    setAttributeMetas(result);
  }, [samples]);

  // --- 属性フィルター状態 ---
  const [attributeFilters, setAttributeFilters] = useState<AttributeFilters>({});
  const [numericRanges, setNumericRanges] = useState<NumericRangeFilters>({});
  const [enabledRanges, setEnabledRanges] = useState<Record<string, boolean>>({});
  const [includeEmptyValues, setIncludeEmptyValues] = useState<Record<string, boolean>>({});
  const [textSearch, setTextSearch] = useState<string>(""); // 追加: テキスト検索状態
  const [openAttributeFilter, setOpenAttributeFilter] = useState(false);

  // --- 密度フィルタ有効性 ---
  useEffect(() => {
    const { filtered, isEmpty } = getDenseClusters(result.clusters || [], maxDensity, minValue);
    setIsDenseGroupEnabled(!isEmpty);
  }, [maxDensity, minValue, result.clusters]);

  // --- 属性・密度フィルタ適用 ---
  function updateFilteredResult(
    maxDensity: number,
    minValue: number,
    attrFilters: AttributeFilters = attributeFilters,
    textSearchString: string = textSearch, // 追加: テキスト検索文字列パラメータ
  ) {
    if (!result) return;
    let filteredArgs = result.arguments;
    let filteredArgIds: string[] = [];
    const hasActiveFilters =
      Object.keys(attrFilters).length > 0 || 
      Object.keys(enabledRanges).filter((k) => enabledRanges[k]).length > 0 ||
      textSearchString.trim() !== ""; // 追加: テキスト検索が有効かどうか
    if (hasActiveFilters) {
      filteredArgs = result.arguments.filter((arg) => {
        if (textSearchString.trim() !== "") {
          const searchLower = textSearchString.trim().toLowerCase();
          const argumentLower = arg.argument.toLowerCase();
          if (!argumentLower.includes(searchLower)) {
            return false;
          }
        }
        
        if (arg.attributes) {
          const passesAttributeFilters = Object.entries(attrFilters).every(([attrName, selectedValues]) => {
            const attrValue = arg.attributes?.[attrName];
            const values = selectedValues as string[];
            if (values.length === 1 && values[0].startsWith("range:")) {
              const [_, minStr, maxStr] = values[0].split(":");
              const min = Number(minStr);
              const max = Number(maxStr);
              const numValue = Number(attrValue);
              return !Number.isNaN(numValue) && numValue >= min && numValue <= max;
            }
            return values.includes(String(attrValue));
          });
          const passesNumericRanges = Object.entries(numericRanges).every(([attrName, range]) => {
            if (!enabledRanges[attrName]) return true;
            const attrValue = arg.attributes?.[attrName];
            if (attrValue === undefined || attrValue === null || attrValue === "") {
              return includeEmptyValues[attrName] || false;
            }
            const numValue = Number(attrValue);
            return !Number.isNaN(numValue) && numValue >= range[0] && numValue <= range[1];
          });
          return passesAttributeFilters && passesNumericRanges;
        }
        return textSearchString.trim() === ""; // テキスト検索がない場合のみ属性なしの引数を許可
      });
      filteredArgIds = filteredArgs.map((arg) => arg.arg_id);
    }
    const clusterIdsWithFilteredArgs = new Set<string>();
    filteredArgs.forEach((arg) => {
      arg.cluster_ids.forEach((clusterId) => {
        clusterIdsWithFilteredArgs.add(clusterId);
      });
    });
    const { filtered: densityFilteredClusters } = getDenseClusters(result.clusters || [], maxDensity, minValue);
    
    // フィルターが適用されていても、すべてのクラスターを表示するが、
    // フィルター条件に合致する引数がないクラスタは特別なプロパティで区別する
    const combinedFilteredClusters = densityFilteredClusters.map(cluster => {
      if (hasActiveFilters && !clusterIdsWithFilteredArgs.has(cluster.id)) {
        // このクラスターにはフィルター条件に合致する引数が存在しないことを示す
        return { ...cluster, allFiltered: true };
      }
      return cluster;
    });
    
    setFilteredResult({
      ...result,
      clusters: combinedFilteredClusters,
      arguments: result.arguments,
      filteredArgumentIds: hasActiveFilters ? filteredArgIds : undefined,
    });
  }

  // --- UIハンドラ群 ---
  function onChangeDensityFilter(maxDensity: number, minValue: number) {
    setMaxDensity(maxDensity);
    setMinValue(minValue);
    if (selectedChart === "scatterDensity" || selectedChart === "scatterAll") {
      updateFilteredResult(maxDensity, minValue);
    }
  }

  function handleApplyAttributeFilters(
    filters: AttributeFilters,
    numericRanges_: NumericRangeFilters,
    includeEmpty: Record<string, boolean>,
    enabledRanges_: Record<string, boolean>,
    textSearchString: string, // 追加: テキスト検索文字列
  ) {
    setAttributeFilters(filters);
    setNumericRanges(numericRanges_);
    setIncludeEmptyValues(includeEmpty);
    setEnabledRanges(enabledRanges_);
    setTextSearch(textSearchString); // 追加: テキスト検索状態を更新
    if (selectedChart === "scatterAll" || selectedChart === "scatterDensity") {
      updateFilteredResult(
        selectedChart === "scatterDensity" ? maxDensity : 1,
        selectedChart === "scatterDensity" ? minValue : 0,
        filters,
        textSearchString, // 追加: テキスト検索文字列を渡す
      );
    }
  }

  // --- フィルター済み標本 ---
  const filteredSamples = useMemo(() => {
    return filterSamples(samples, attributeFilters, numericRanges, enabledRanges, includeEmptyValues);
  }, [samples, attributeFilters, numericRanges, enabledRanges, includeEmptyValues]);

  // --- クラスタ表示 ---
  const clustersToDisplay =
    selectedChart === "scatterDensity"
      ? filteredResult.clusters.filter((c) => c.level === Math.max(...filteredResult.clusters.map((c) => c.level)))
      : result.clusters.filter((c) => c.level === 1);

  // --- その他UIハンドラ ---
  const handleCloseDisplaySetting = () => setOpenDensityFilterSetting(false);
  const handleToggleClusterLabels = (value: boolean) => setShowClusterLabels(value);
  const handleCloseAttributeFilter = () => setOpenAttributeFilter(false);
  const handleChartChange = (selectedChart: string) => {
    setSelectedChart(selectedChart);
    if (selectedChart === "scatterAll") updateFilteredResult(1, 0, attributeFilters, textSearch);
    if (selectedChart === "treemap") {
      // 属性フィルターをリセットせずに維持
      updateFilteredResult(1, 0, attributeFilters, textSearch);
    }
    if (selectedChart === "scatterDensity") updateFilteredResult(maxDensity, minValue, attributeFilters, textSearch);
  };
  const handleClickDensitySetting = () => setOpenDensityFilterSetting(true);
  const handleClickFullscreen = () => setIsFullscreen(true);
  const handleOpenAttributeFilter = () => setOpenAttributeFilter(true);
  const handleExitFullscreen = () => setIsFullscreen(false);
  const handleTreeZoom = (value: string) => setTreemapLevel(value);

  // --- UI ---
  return (
    <div>
      {openDensityFilterSetting && (
        <DisplaySettingDialog
          currentMaxDensity={maxDensity}
          currentMinValue={minValue}
          onClose={handleCloseDisplaySetting}
          onChangeFilter={onChangeDensityFilter}
          showClusterLabels={showClusterLabels}
          onToggleClusterLabels={handleToggleClusterLabels}
        />
      )}
      {openAttributeFilter && (
        <AttributeFilterDialog
          onClose={handleCloseAttributeFilter}
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
        onChange={handleChartChange}
        onClickDensitySetting={handleClickDensitySetting}
        onClickFullscreen={handleClickFullscreen}
        isDenseGroupEnabled={isDenseGroupEnabled}
        // The following props are for the new AttentionFilter button
        onClickAttentionFilter={handleOpenAttributeFilter} // Assuming this is the correct handler
        isAttentionFilterEnabled={attributeMetas.length > 0} // Assuming this is the correct condition
        showAttentionFilterBadge={
          (Object.keys(attributeFilters).length > 0 ||
            Object.keys(enabledRanges).filter((k) => enabledRanges[k]).length > 0 ||
            textSearch.trim() !== "")
        }
        attentionFilterBadgeCount={(() => {
          const allFilteredAttributes = new Set([
            ...Object.keys(attributeFilters),
            ...Object.keys(enabledRanges).filter((k) => enabledRanges[k]),
          ]);
          if (textSearch.trim() !== "") allFilteredAttributes.add("textSearch");
          return allFilteredAttributes.size;
        })()}
      />
      <Chart
        result={filteredResult}
        selectedChart={selectedChart}
        isFullscreen={isFullscreen}
        onExitFullscreen={handleExitFullscreen}
        showClusterLabels={showClusterLabels}
        onToggleClusterLabels={handleToggleClusterLabels}
        treemapLevel={treemapLevel}
        onTreeZoom={handleTreeZoom}
        filterState={{
          attributeFilters,
          numericRanges,
          enabledRanges,
          includeEmptyValues,
          textSearch, // 追加: テキスト検索状態を渡す
        }}
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
