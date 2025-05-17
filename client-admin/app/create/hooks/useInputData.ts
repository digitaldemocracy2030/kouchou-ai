import { toaster } from "@/components/ui/toaster";
import { useCallback, useState } from "react";
import { deleteSpreadsheetData, getSpreadsheetData, importSpreadsheet } from "../api/spreadsheet";
import { parseCsv } from "../parseCsv";
import type { InputType, SpreadsheetComment } from "../types";
import { getBestCommentColumn } from "../utils/columnScorer";
import { showErrorToast } from "../utils/error-handler";

/**
 * 入力データを管理するカスタムフック
 */
export function useInputData(onDataLoaded: (commentCount: number) => void) {
  // 入力タイプの状態
  const [inputType, setInputType] = useState<InputType>("file");

  // CSVファイル関連の状態
  const [csv, setCsv] = useState<File | null>(null);

  // スプレッドシート関連の状態
  const [spreadsheetUrl, setSpreadsheetUrl] = useState<string>("");
  const [spreadsheetImported, setSpreadsheetImported] = useState<boolean>(false);
  const [spreadsheetLoading, setSpreadsheetLoading] = useState<boolean>(false);
  const [spreadsheetData, setSpreadsheetData] = useState<SpreadsheetComment[]>([]);
  const [importedId, setImportedId] = useState<string>("");

  // カラム関連の状態
  const [csvColumns, setCsvColumns] = useState<string[]>([]);
  const [selectedCommentColumn, setSelectedCommentColumn] = useState<string>("");
  const [selectedAttributeColumns, setSelectedAttributeColumns] = useState<string[]>([]);

  /**
   * 最適なカラムを選択する関数
   */
  const selectBestColumn = useCallback(
    (data: Record<string, unknown>[]) => {
      if (data.length === 0) return;
      const columns = Object.keys(data[0]);
      setCsvColumns(columns);

      // スコアに基づいて最適なカラムを選択
      const bestColumn = getBestCommentColumn(data);
      if (bestColumn) {
        setSelectedCommentColumn(bestColumn);
      }

      onDataLoaded(data.length);
    },
    [onDataLoaded],
  );

  /**
   * CSVファイル変更時のハンドラー
   */
  const handleCsvChange = useCallback(
    async (file: File | null) => {
      setCsv(file);
      if (file) {
        try {
          const parsed = await parseCsv(file);
          if (parsed.length > 0) {
            selectBestColumn(parsed as unknown as Record<string, unknown>[]);
          }
        } catch (error) {
          showErrorToast(toaster, error, "CSVファイルの読み込みに失敗しました");
        }
      } else {
        setCsvColumns([]);
        setSelectedCommentColumn("");
        setSelectedAttributeColumns([]);
      }
    },
    [selectBestColumn],
  );

  /**
   * スプレッドシートのインポート
   */
  const handleImportSpreadsheet = useCallback(
    async (id: string) => {
      if (!spreadsheetUrl.trim()) {
        toaster.create({
          type: "error",
          title: "入力エラー",
          description: "スプレッドシートのURLを入力してください",
        });
        return;
      }

      setSpreadsheetLoading(true);
      try {
        await importSpreadsheet(spreadsheetUrl, id);
        setImportedId(id);

        // スプレッドシートのデータを取得
        const commentData = await getSpreadsheetData(id);
        setSpreadsheetData(commentData.comments);

        if (commentData.comments.length > 0) {
          selectBestColumn(commentData.comments as unknown as Record<string, unknown>[]);
        }

        toaster.create({
          type: "success",
          title: "成功",
          description: `スプレッドシートのデータ ${commentData.comments.length} 件を取得しました`,
        });
        setSpreadsheetImported(true);
      } catch (error) {
        showErrorToast(toaster, error, "データ取得エラー");
        setSpreadsheetImported(false);
      } finally {
        setSpreadsheetLoading(false);
      }
    },
    [spreadsheetUrl, selectBestColumn],
  );

  /**
   * スプレッドシートデータのクリア
   */
  const handleClearSpreadsheetData = useCallback(async () => {
    try {
      setSpreadsheetLoading(true);
      if (importedId) {
        await deleteSpreadsheetData(importedId);
      }

      toaster.create({
        type: "success",
        title: "成功",
        description: "データをクリアしました",
      });
    } catch (error) {
      showErrorToast(toaster, error, "警告");
    } finally {
      // UIの状態をリセット
      setSpreadsheetImported(false);
      setSpreadsheetData([]);
      setSpreadsheetLoading(false);
      setImportedId("");
      setSpreadsheetUrl("");
      setSelectedCommentColumn("");
      setSelectedAttributeColumns([]);
      setCsvColumns([]);
    }
  }, [importedId]);

  /**
   * 入力タイプ変更時のハンドラー
   */
  const handleInputTypeChange = useCallback(
    (newType: InputType) => {
      setInputType(newType);

      if (newType === "file" && csv) {
        // CSVのカラムを再構築
        parseCsv(csv).then((parsed) => {
          if (parsed.length > 0) {
            selectBestColumn(parsed as unknown as Record<string, unknown>[]);
          }
        });
      } else if (newType === "spreadsheet" && spreadsheetData.length > 0) {
        // スプレッドシートのカラムを再構築
        selectBestColumn(spreadsheetData as unknown as Record<string, unknown>[]);
      } else {
        // データがない場合はカラムリセット
        setCsvColumns([]);
        setSelectedCommentColumn("");
        setSelectedAttributeColumns([]);
      }
    },
    [csv, spreadsheetData, selectBestColumn],
  );

  /**
   * スプレッドシートのインポートが可能かどうか
   */
  const canImport = spreadsheetUrl.trim() !== "" && !spreadsheetImported;

  return {
    inputType,
    csv,
    spreadsheetUrl,
    spreadsheetImported,
    spreadsheetLoading,
    spreadsheetData,
    importedId,
    csvColumns,
    selectedCommentColumn,
    selectedAttributeColumns, 
    canImport,
    setInputType: handleInputTypeChange,
    setCsv: handleCsvChange,
    setSpreadsheetUrl,
    setSelectedCommentColumn,
    setSelectedAttributeColumns,
    setCsvColumns,
    importSpreadsheet: handleImportSpreadsheet,
    clearSpreadsheetData: handleClearSpreadsheetData,
  };
}
