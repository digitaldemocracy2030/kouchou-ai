// 属性フィルターのユーティリティ（型定義・フィルタロジック・メタデータ計算）
import type { Argument } from "@/type";

// ============================================================================
// 型定義
// ============================================================================

export type AttributeFilters = Record<string, string[]>;
export type NumericRangeFilters = Record<string, [number, number]>;

export type AttributeMeta = {
  name: string;
  type: "numeric" | "categorical";
  values: string[];
  valueCounts: Record<string, number>;
  numericRange?: [number, number];
};

export type FilterParams = {
  attributeFilters: AttributeFilters;
  numericRanges: NumericRangeFilters;
  enabledRanges: Record<string, boolean>;
  includeEmptyValues: Record<string, boolean>;
  textSearch: string;
};

// ============================================================================
// フィルタロジック
// ============================================================================

/**
 * フィルタ条件がアクティブかどうかを判定する
 */
export function hasActiveFilters(params: FilterParams): boolean {
  return (
    Object.keys(params.attributeFilters).length > 0 ||
    Object.values(params.enabledRanges).some(Boolean) ||
    params.textSearch.trim() !== ""
  );
}

/**
 * フィルタ条件に合致する引数IDのリストを返す。
 * フィルタ条件が空の場合はundefinedを返す（全件表示）。
 */
export function filterArgumentIds(args: Argument[], params: FilterParams): string[] | undefined {
  if (!hasActiveFilters(params)) return undefined;

  const { attributeFilters, numericRanges, enabledRanges, includeEmptyValues, textSearch } = params;
  const searchLower = textSearch.trim().toLowerCase();

  return args
    .filter((arg) => {
      // テキスト検索
      if (searchLower && !arg.argument.toLowerCase().includes(searchLower)) {
        return false;
      }

      // 属性がない場合、カテゴリ/数値フィルタはマッチ不可なので除外。
      // テキスト検索のみアクティブならテキストマッチで判定する。
      if (!arg.attributes) {
        return !!searchLower;
      }

      // カテゴリフィルタ（属性間はAND、値間はOR）
      for (const [attr, values] of Object.entries(attributeFilters)) {
        if (values.length === 0) continue;
        const attrValue = String(arg.attributes[attr] ?? "");
        if (!values.includes(attrValue)) return false;
      }

      // 数値レンジフィルタ
      for (const [attr, range] of Object.entries(numericRanges)) {
        if (!enabledRanges[attr]) continue;
        const rawValue = arg.attributes[attr];
        const trimmed = rawValue == null ? "" : String(rawValue).trim();
        if (trimmed === "") {
          if (!includeEmptyValues[attr]) return false;
        } else {
          const numValue = Number(trimmed);
          if (Number.isNaN(numValue) || numValue < range[0] || numValue > range[1]) return false;
        }
      }

      return true;
    })
    .map((arg) => arg.arg_id);
}

/**
 * アクティブなフィルタ数を計算する
 */
export function countActiveFilters(params: FilterParams): number {
  const attrCount = new Set([
    ...Object.keys(params.attributeFilters),
    ...Object.keys(params.enabledRanges).filter((k) => params.enabledRanges[k]),
  ]).size;
  return attrCount + (params.textSearch.trim() !== "" ? 1 : 0);
}

// ============================================================================
// メタデータ計算
// ============================================================================

/**
 * 引数の属性情報からメタデータを計算する
 */
export function computeAttributeMetas(args: Argument[]): AttributeMeta[] {
  const attrMap: Record<
    string,
    {
      valueSet: Set<string>;
      valueCounts: Map<string, number>;
      isNumeric: boolean;
      min?: number;
      max?: number;
    }
  > = {};

  for (const arg of args) {
    if (!arg.attributes) continue;
    for (const [name, rawValue] of Object.entries(arg.attributes)) {
      const value = rawValue == null ? "" : String(rawValue);
      if (!attrMap[name]) {
        attrMap[name] = { valueSet: new Set(), valueCounts: new Map(), isNumeric: true };
      }
      const info = attrMap[name];
      info.valueSet.add(value);
      info.valueCounts.set(value, (info.valueCounts.get(value) ?? 0) + 1);
      if (value.trim() !== "") {
        const num = Number(value);
        if (Number.isNaN(num)) {
          info.isNumeric = false;
        } else if (info.isNumeric) {
          if (info.min === undefined || num < info.min) info.min = num;
          if (info.max === undefined || num > info.max) info.max = num;
        }
      }
    }
  }

  return Object.entries(attrMap).map(([name, info]) => {
    const values = Array.from(info.valueSet).filter((v) => v !== "").sort();
    const valueCounts: Record<string, number> = {};
    for (const v of values) valueCounts[v] = info.valueCounts.get(v) ?? 0;
    return {
      name,
      type: info.isNumeric ? "numeric" : "categorical",
      values,
      valueCounts,
      numericRange:
        info.isNumeric && values.length > 0 && info.min !== undefined && info.max !== undefined
          ? [info.min, info.max]
          : undefined,
    };
  });
}
