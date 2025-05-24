/**
 * IDのバリデーション
 * 英小文字、数字、ハイフンのみ使用可能
 * @param id バリデーション対象のID
 * @returns バリデーション結果
 */
export function isValidId(id: string): boolean {
  return /^[a-z0-9](?:[a-z0-9-]*[a-z0-9])?$/.test(id) && id.length <= 255;
}

/**
 * フォーム入力値のバリデーション
 * @param values バリデーション対象の値
 * @returns バリデーション結果と、エラーメッセージ
 */
export function validateFormValues({
  input,
  question,
  intro,
  clusterLv1,
  clusterLv2,
  model,
  extractionPrompt,
  inputType,
  csv,
  spreadsheetImported,
  selectedCommentColumn,
  csvColumns,
  selectedAttributeColumns,
  provider,
  modelOptions,
}: {
  input: string;
  question: string;
  intro: string;
  clusterLv1: number;
  clusterLv2: number;
  model: string;
  extractionPrompt: string;
  inputType: string;
  csv: File | null;
  spreadsheetImported: boolean;
  selectedCommentColumn: string;
  csvColumns: string[];
  selectedAttributeColumns?: string[];
  provider?: string;
  modelOptions?: { value: string; label: string }[];
}): { isValid: boolean; errorMessage?: string } {
  // 共通チェック
  const commonCheck = [
    isValidId(input),
    //タイトル、概要は必須から省略時自動設定へ
    clusterLv1 > 0,
    clusterLv2 > 0,
    model.length > 0,
    extractionPrompt.length > 0,
  ].every(Boolean);

  if (!commonCheck) {
    return {
      isValid: false,
      errorMessage: "全ての項目が入力されているか確認してください",
    };
  }

  // 入力ソースのチェック
  const sourceCheck = (inputType === "file" && !!csv) || (inputType === "spreadsheet" && spreadsheetImported);

  if (!sourceCheck) {
    return {
      isValid: false,
      errorMessage: "入力データが選択されていません",
    };
  }

  // カラム選択のチェック
  if (csvColumns.length > 0 && !selectedCommentColumn) {
    return {
      isValid: false,
      errorMessage: "コメントカラムを選択してください",
    };
  }

  if (provider === "local" && modelOptions && modelOptions.length === 0) {
    return {
      isValid: false,
      errorMessage: "LocalLLMのモデルリストが空です。モデル取得ボタンを押してモデルリストを取得してください。",
    };
  }

  return { isValid: true };
}
