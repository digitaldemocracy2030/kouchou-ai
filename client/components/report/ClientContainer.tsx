"use client";

import { SelectChartButton } from "@/components/charts/SelectChartButton";
import { AttributeFilterDialog, type AttributeFilters, type NumericRangeFilters } from "@/components/report/AttributeFilterDialog";
import { Chart } from "@/components/report/Chart";
import { ClusterOverview } from "@/components/report/ClusterOverview";
import { DisplaySettingDialog } from "@/components/report/DisplaySettingDialog";
import { Tooltip } from "@/components/ui/tooltip";
import type { Cluster, Result } from "@/type";
import { Box, Button, Icon } from "@chakra-ui/react";
import { Filter } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import { filterSamples } from "./attributeFilterUtils";

type Props = {
  result: Result;
};

export function ClientContainer({ result }: Props) {
  const [filteredResult, setFilteredResult] = useState<Result>(result);
  const [openDensityFilterSetting, setOpenDensityFilterSetting] = useState(false);
  const [selectedChart, setSelectedChart] = useState("scatterAll");
  const [maxDensity, setMaxDensity] = useState(0.2);
  const [minValue, setMinValue] = useState(5);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [isDenseGroupEnabled, setIsDenseGroupEnabled] = useState(true);
  const [showClusterLabels, setShowClusterLabels] = useState(true);
  const [treemapLevel, setTreemapLevel] = useState("0");

  // 標本データ生成（全コメントをRecord<string, string>で配列化）
  const samples = useMemo(() => {
    return result.arguments.map((arg) => {
      if (arg.attributes) {
        // すべてstring化
        const rec: Record<string, string> = {};
        Object.entries(arg.attributes).forEach(([k, v]) => {
          rec[k] = v == null ? "" : String(v);
        });
        return rec;
      }
      return {};
    });
  }, [result]);

  // 属性フィルターの状態
  const [attributeFilters, setAttributeFilters] = useState<AttributeFilters>({});
  const [numericRanges, setNumericRanges] = useState<NumericRangeFilters>({});
  const [enabledRanges, setEnabledRanges] = useState<Record<string, boolean>>({});
  const [includeEmptyValues, setIncludeEmptyValues] = useState<Record<string, boolean>>({});
  const [openAttributeFilter, setOpenAttributeFilter] = useState(false);

  // 利用可能な属性と値のセットを抽出
  const availableAttributes = useMemo(() => {
    const attributes: Record<string, Set<string>> = {};

    // 全ての意見から属性を抽出
    result.arguments.forEach((arg) => {
      // attributes フィールドからデータを抽出
      if (arg.attributes) {
        Object.entries(arg.attributes).forEach(([key, value]) => {
          if (value !== undefined && value !== null) {
            if (!attributes[key]) {
              attributes[key] = new Set<string>();
            }
            attributes[key].add(String(value));
          }
        });
      }
    });

    // Set を配列に変換して返す
    const attributesArray: Record<string, string[]> = {};
    Object.entries(attributes).forEach(([key, valueSet]) => {
      attributesArray[key] = Array.from(valueSet).sort();
    });

    return attributesArray;
  }, [result]);

  // 属性タイプの検出と数値範囲の計算をキャッシュ
  const attributeTypes = useMemo(() => {
    // 数値のみの属性と通常の属性を判別
    const typeMap: Record<string, "numeric" | "categorical"> = {};

    Object.entries(availableAttributes).forEach(([attribute, values]) => {
      // 全ての値が数値に変換可能かチェック
      const isNumeric = (values as string[]).every((value: string) => {
        const trimmedValue = value.trim();
        return trimmedValue === "" || !Number.isNaN(Number(trimmedValue));
      });

      typeMap[attribute] = isNumeric && (values as string[]).length > 0 ? "numeric" : "categorical";
    });

    return typeMap;
  }, [availableAttributes]);

  // 数値属性の範囲をキャッシュ
  const numericRangesMemo = useMemo(() => {
    const ranges: Record<string, [number, number]> = {};

    Object.entries(availableAttributes).forEach(([attribute, values]) => {
      if (attributeTypes[attribute] === "numeric") {
        // 数値に変換
        const numericValues = (values as string[])
          .map((v: string) => (v.trim() === "" ? Number.NaN : Number(v)))
          .filter((v: number) => !Number.isNaN(v));
        // 数値が存在しない場合はスキップ
        if (numericValues.length === 0) return;

        // 最小値と最大値を設定
        ranges[attribute] = [Math.min(...numericValues), Math.max(...numericValues)];
      }
    });

    return ranges;
  }, [availableAttributes, attributeTypes]);

  // maxDensityやminValueが変化するたびに密度フィルターの結果をチェック
  useEffect(() => {
    const { filtered, isEmpty } = getDenseClusters(result.clusters || [], maxDensity, minValue);
    setIsDenseGroupEnabled(!isEmpty);
  }, [maxDensity, minValue, result.clusters]);

  // 属性フィルタと密度フィルタを組み合わせて適用する関数
  function updateFilteredResult(
    maxDensity: number,
    minValue: number,
    attrFilters: AttributeFilters = attributeFilters,
  ) {
    if (!result) return;

    // 1. 属性フィルタに基づいて引数をフィルタリング
    let filteredArgs = result.arguments;
    let filteredArgIds: string[] = [];

    // カテゴリーフィルターか数値フィルターのいずれかがアクティブかチェック
    const hasActiveFilters =
      Object.keys(attrFilters).length > 0 || Object.keys(enabledRanges).filter((k) => enabledRanges[k]).length > 0;

    if (hasActiveFilters) {
      // フィルター条件を満たす引数を抽出
      filteredArgs = result.arguments.filter((arg) => {
        // attributes フィールドを確認
        if (arg.attributes) {
          // カテゴリーフィルター条件をチェック
          const passesAttributeFilters = Object.entries(attrFilters).every(([attrName, selectedValues]) => {
            const attrValue = arg.attributes?.[attrName];
            const values = selectedValues as string[];

            // 数値範囲フィルターの処理
            if (values.length === 1 && values[0].startsWith("range:")) {
              const [_, minStr, maxStr] = values[0].split(":");
              const min = Number(minStr);
              const max = Number(maxStr);
              const numValue = Number(attrValue);

              return !Number.isNaN(numValue) && numValue >= min && numValue <= max;
            }

            // 通常のチェックボックスフィルターの処理
            return values.includes(String(attrValue));
          });

          // 数値範囲フィルター条件をチェック
          const passesNumericRanges = Object.entries(numericRanges).every(([attrName, range]) => {
            // フィルターが有効でない場合はパスする
            if (!enabledRanges[attrName]) return true;

            const attrValue = arg.attributes?.[attrName];

            // 空値の場合のチェック
            if (attrValue === undefined || attrValue === null || attrValue === "") {
              return includeEmptyValues[attrName] || false;
            }

            // 数値範囲チェック
            const numValue = Number(attrValue);
            const typedRange = range as [number, number];
            return !Number.isNaN(numValue) && numValue >= typedRange[0] && numValue <= typedRange[1];
          });

          return passesAttributeFilters && passesNumericRanges;
        }

        return false;
      });

      // フィルター条件を満たす引数のIDリストを作成
      filteredArgIds = filteredArgs.map((arg) => arg.arg_id);
    }

    // 2. フィルタされた引数を含むクラスタIDを集める
    const clusterIdsWithFilteredArgs = new Set<string>();
    filteredArgs.forEach((arg) => {
      arg.cluster_ids.forEach((clusterId) => {
        clusterIdsWithFilteredArgs.add(clusterId);
      });
    });

    // 3. 密度フィルタを適用
    const { filtered: densityFilteredClusters } = getDenseClusters(result.clusters || [], maxDensity, minValue);

    // 4. 両方のフィルタを組み合わせる
    const combinedFilteredClusters = densityFilteredClusters.filter(
      (cluster) => !hasActiveFilters || clusterIdsWithFilteredArgs.has(cluster.id),
    );

    setFilteredResult({
      ...result,
      clusters: combinedFilteredClusters,
      arguments: result.arguments, // 全ての引数を含め、グレーアウト表示のために使用
      // 新しいプロパティとしてフィルター条件に合致する引数IDのリストを追加
      filteredArgumentIds: hasActiveFilters ? filteredArgIds : undefined,
    });
  }

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
  ) {
    setAttributeFilters(filters);
    setNumericRanges(numericRanges_);
    setIncludeEmptyValues(includeEmpty);
    setEnabledRanges(enabledRanges_);

    // フィルター適用後にチャート表示を更新
    if (selectedChart === "scatterAll" || selectedChart === "scatterDensity") {
      // 属性フィルターと既存の密度フィルターを組み合わせて適用
      updateFilteredResult(
        selectedChart === "scatterDensity" ? maxDensity : 1,
        selectedChart === "scatterDensity" ? minValue : 0,
        filters,
      );
    }
  }

  // フィルター済み標本を計算
  const filteredSamples = useMemo(() => {
    return filterSamples(samples, attributeFilters, numericRanges, enabledRanges, includeEmptyValues);
  }, [samples, attributeFilters, numericRanges, enabledRanges, includeEmptyValues]);

  // 表示するクラスタを選択
  const clustersToDisplay =
    selectedChart === "scatterDensity"
      ? filteredResult.clusters.filter((c: Cluster) => c.level === Math.max(...filteredResult.clusters.map((c: Cluster) => c.level)))
      : result.clusters.filter((c: Cluster) => c.level === 1);

  const handleCloseDisplaySetting = () => {
    setOpenDensityFilterSetting(false);
  };

  const handleToggleClusterLabels = (value: boolean) => {
    setShowClusterLabels(value);
  };

  const handleCloseAttributeFilter = () => {
    setOpenAttributeFilter(false);
  };

  const handleChartChange = (selectedChart: string) => {
    setSelectedChart(selectedChart);
    if (selectedChart === "scatterAll") {
      updateFilteredResult(1, 0);
    }
    if (selectedChart === "treemap") {
      // treemapでは属性フィルターも解除する必要がある
      setAttributeFilters({});
      updateFilteredResult(1, 0, {});
    }
    if (selectedChart === "scatterDensity") {
      updateFilteredResult(maxDensity, minValue);
    }
  };

  const handleClickDensitySetting = () => {
    setOpenDensityFilterSetting(true);
  };

  const handleClickFullscreen = () => {
    setIsFullscreen(true);
  };

  const handleOpenAttributeFilter = () => {
    setOpenAttributeFilter(true);
  };

  const handleExitFullscreen = () => {
    setIsFullscreen(false);
  };

  const handleTreeZoom = (value: string) => {
    setTreemapLevel(value);
  };

  return (
    <Box as="div">
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
          samples={samples}
          initialFilters={attributeFilters}
          initialNumericRanges={numericRanges}
          initialEnabledRanges={enabledRanges}
          initialIncludeEmptyValues={includeEmptyValues}
        />
      )}

      <Box display="flex" gap={2} mb={3}>
        <SelectChartButton
          selected={selectedChart}
          onChange={handleChartChange}
          onClickDensitySetting={handleClickDensitySetting}
          onClickFullscreen={handleClickFullscreen}
          isDenseGroupEnabled={isDenseGroupEnabled}
          attributeFilterButton={
            Object.keys(availableAttributes).length > 0 ? (
              <Tooltip content={"属性フィルタ"} openDelay={0} closeDelay={0}>
                <Button onClick={handleOpenAttributeFilter} variant="outline" h={"50px"}>
                  <Box display="flex" alignItems="center" gap={1}>
                    <Icon>
                      <Filter size={16} />
                    </Icon>
                    {(Object.keys(attributeFilters).length > 0 ||
                      Object.keys(enabledRanges).filter((k) => enabledRanges[k]).length > 0) && (
                      <Box as="span" fontSize="xs" bg="cyan.500" color="white" p="1" borderRadius="md" minW="5">
                        {(() => {
                          // カテゴリーフィルターの属性数
                          const categoryFilterCount = Object.keys(attributeFilters).length;
                          // 有効な数値フィルターの属性数
                          const numericFilterCount = Object.keys(enabledRanges).filter((k) => enabledRanges[k]).length;
                          // 合計をユニークな属性数として計算（重複カウント防止）
                          const allFilteredAttributes = new Set([
                            ...Object.keys(attributeFilters),
                            ...Object.keys(enabledRanges).filter((k) => enabledRanges[k]),
                          ]);
                          return allFilteredAttributes.size;
                        })()}
                      </Box>
                    )}
                  </Box>
                </Button>
              </Tooltip>
            ) : null
          }
        />
      </Box>

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
        }}
      />

      {clustersToDisplay.map((c: Cluster) => (
        <ClusterOverview key={c.id} cluster={c} />
      ))}
    </Box>
  );
}

function getDenseClusters(
  clusters: Cluster[],
  maxDensity: number,
  minValue: number,
): { filtered: Cluster[]; isEmpty: boolean } {
  // 全意見グループの中で一番大きい level を deepestLevel として取得します。
  const deepestLevel = clusters.reduce((maxLevel, cluster) => Math.max(maxLevel, cluster.level), 0);

  console.log("=== Dense Cluster Extraction ===");
  console.log(`Filter settings: maxDensity=${maxDensity}, minValue=${minValue}`);

  const deepestLevelClusters = clusters.filter((c) => c.level === deepestLevel);
  console.log(`Total clusters at deepest level (${deepestLevel}): ${deepestLevelClusters.length}`);

  for (const cluster of deepestLevelClusters) {
    console.log(
      `Cluster ID: ${cluster.id}, Label: ${cluster.label}, Density: ${cluster.density_rank_percentile}, Elements: ${cluster.value}`,
    );
  }

  const filteredDeepestLevelClusters = deepestLevelClusters
    .filter((c) => c.density_rank_percentile <= maxDensity)
    .filter((c) => c.value >= minValue);

  console.log(`Clusters after filtering: ${filteredDeepestLevelClusters.length}`);
  console.log(filteredDeepestLevelClusters);
  console.log("=== End of Dense Cluster Extraction ===");

  return {
    filtered: [...clusters.filter((c) => c.level !== deepestLevel), ...filteredDeepestLevelClusters],
    isEmpty: filteredDeepestLevelClusters.length === 0,
  };
}
