// 属性フィルター条件に従って標本配列をフィルタリングするユーティリティ
import type { AttributeFilters } from "./AttributeFilterDialog";

export type NumericRangeFilters = Record<string, [number, number]>;

/**
 * 標本配列をフィルター条件に従ってフィルタリングする
 */
export function filterSamples(
  samples: Array<Record<string, string>>,
  filters: AttributeFilters,
  numericRanges: NumericRangeFilters,
  enabledRanges: Record<string, boolean>,
  includeEmpty: Record<string, boolean>,
): Array<Record<string, string>> {
  // フィルター条件が空なら全て表示
  if (Object.keys(filters).length === 0 && Object.keys(enabledRanges).filter((k) => enabledRanges[k]).length === 0) {
    return samples;
  }

  return samples.filter((sample) => {
    // カテゴリ属性
    for (const [attr, values] of Object.entries(filters)) {
      if (values.length > 0 && values[0] !== undefined) {
        if (!values.includes(sample[attr] ?? "")) {
          return false;
        }
      }
    }

    // 数値属性
    for (const [attr, range] of Object.entries(numericRanges)) {
      if (enabledRanges[attr]) {
        const value = sample[attr]?.trim() ?? "";
        if (value === "") {
          if (!includeEmpty[attr]) return false;
        } else {
          const num = Number(value);
          if (Number.isNaN(num) || num < range[0] || num > range[1]) return false;
        }
      }
    }
    return true;
  });
}

/**
 * 引数IDからフィルター済みの引数IDリストを生成する
 * @param argumentIds 全引数ID
 * @param samples 全標本
 * @param filteredSamples フィルター済み標本
 */
export function getFilteredArgumentIds(
  argumentIds: string[],
  samples: Array<Record<string, string>>,
  filteredSamples: Array<Record<string, string>>,
): string[] {
  // フィルター済み標本のインデックスセットを作成
  const filteredIndices = new Set<number>();
  for (const fs of filteredSamples) {
    const idx = samples.findIndex((s) => Object.entries(s).every(([k, v]) => fs[k] === v));
    if (idx >= 0) filteredIndices.add(idx);
  }

  // フィルター済みのインデックスに対応する引数IDを返す
  return Array.from(filteredIndices).map((idx) => argumentIds[idx]);
}
