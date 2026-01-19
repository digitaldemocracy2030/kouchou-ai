import type { Report } from "@/type";

export function analysisInfo(report: Report) {
  const tokenUsageInput = report.tokenUsageInput?.toLocaleString();
  const tokenUsageOutput = report.tokenUsageOutput?.toLocaleString();
  const tokenUsageTotal = report.tokenUsage?.toLocaleString();
  const estimatedCost = typeof report.estimatedCost === "number" ? `$${report.estimatedCost.toFixed(6)}` : "情報なし";
  const model = report.provider && report.model ? `${report.provider} ${report.model}` : null;

  const hasInput = report.tokenUsageInput !== undefined && report.tokenUsageOutput !== undefined;
  const hasTotal = report.tokenUsage !== undefined;

  if (hasInput) {
    return {
      hasInput,
      hasTotal,
      estimatedCost,
      model,
      tokenUsageInput,
      tokenUsageOutput,
    };
  }

  if (hasTotal) {
    return {
      hasInput,
      hasTotal,
      estimatedCost,
      model,
      tokenUsageTotal: `${tokenUsageTotal} (詳細なし)`,
    };
  }

  return {
    hasInput,
    hasTotal,
    estimatedCost,
    model,
    tokenUsageTotal: "情報なし",
  };
}
