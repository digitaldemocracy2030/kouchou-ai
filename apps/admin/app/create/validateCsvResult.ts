import type { ParseResult } from "papaparse";

/** 両版で同じ入力判定を使う。行番号は物理行でなく、ヘッダーを除くデータの位置。 */
export function validateCsvResult(result: ParseResult<Record<string, unknown>>): void {
  const error = result.errors.find((item) => item.code !== "UndetectableDelimiter");
  if (error) {
    const position =
      error.type === "FieldMismatch" && typeof error.row === "number" ? `データの${error.row + 1}件目: ` : "";
    const remedies: Record<string, string> = {
      MissingQuotes: '引用符（"）が閉じられていません。引用符の対応を確認し、CSVを保存し直してください。',
      InvalidQuotes:
        '引用符（"）の使い方が不正です。値の中の引用符を二重にするか、表計算ソフトからCSVを保存し直してください。',
      TooManyFields: 'ヘッダーより列が多くなっています。本文にカンマを含む場合は引用符（"）で囲んでください。',
      TooFewFields: "ヘッダーより列が少なくなっています。各データの列数をヘッダーに揃えてください。",
    };
    throw new Error(
      position + (remedies[error.code] ?? "CSVの形式を確認し、表計算ソフトからCSVを保存し直してください。"),
    );
  }
  const fields = result.meta.fields ?? [];
  if (result.data.length === 0 || fields.length === 0) {
    throw new Error("分析するデータがありません。ヘッダーに続けてコメントを入力してください。");
  }
  if (fields.some((field) => !field.trim())) {
    throw new Error("名前のない列があります。ヘッダーの各列に名前を付けてください。");
  }
  const renamed = (result.meta as { renamedHeaders?: Record<string, string> }).renamedHeaders;
  if (new Set(fields).size !== fields.length || (renamed && Object.keys(renamed).length > 0)) {
    throw new Error("同じ名前の列があります。ヘッダーの列名が重複しないように変更してください。");
  }
}
