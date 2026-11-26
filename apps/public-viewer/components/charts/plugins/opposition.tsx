import { Split } from "lucide-react";
import { OppositionChart } from "../OppositionChart";
import { OPPOSITION_CHART, getOppositionAxes } from "./opposition-data";
import type { ChartPlugin } from "./types";

export const oppositionPlugin: ChartPlugin = {
  manifest: {
    id: OPPOSITION_CHART,
    name: "対立軸ビュー",
    description: "同じ話題の中で意見がどこで分かれるかを、事前計算した対立軸ごとに読む",
    version: "0.1.0",
    icon: Split,
    modes: [
      {
        id: OPPOSITION_CHART,
        label: "対立",
        icon: Split,
        layout: "flow",
        canBeDisabled: true,
        isDisabled: (result) => getOppositionAxes(result).length === 0,
      },
    ],
  },
  canHandle: (mode) => mode === OPPOSITION_CHART,
  render: ({
    result,
    modeResult,
    filteredArgumentIds,
    oppositionClusterId,
    oppositionSelection,
    onOppositionSelectionChange,
    onBackFromOpposition,
  }) => (
    <OppositionChart
      key={oppositionClusterId}
      result={result}
      axes={getOppositionAxes(modeResult ?? result)}
      filteredArgumentIds={filteredArgumentIds}
      initialClusterId={oppositionClusterId}
      selection={oppositionSelection}
      onSelectionChange={onOppositionSelectionChange}
      onBack={onBackFromOpposition}
    />
  ),
};
