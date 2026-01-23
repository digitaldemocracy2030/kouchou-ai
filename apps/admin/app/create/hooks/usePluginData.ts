import { toaster } from "@/components/ui/toaster";
import type { PluginManifest } from "@/type.d";
import { useCallback, useEffect, useState } from "react";
import { getPlugins, importPluginData, previewPluginData, validatePluginSource } from "../api/plugins";
import type { PluginState, SpreadsheetComment } from "../types";
import { getBestCommentColumn } from "../utils/columnScorer";
import { showErrorToast } from "../utils/error-handler";

/**
 * プラグインデータを管理するカスタムフック
 */
export function usePluginData(onDataLoaded: (commentCount: number) => void) {
  // 利用可能なプラグイン一覧
  const [plugins, setPlugins] = useState<PluginManifest[]>([]);
  const [pluginsLoading, setPluginsLoading] = useState<boolean>(true);

  // プラグインごとの状態（pluginId -> PluginState）
  const [pluginStates, setPluginStates] = useState<Record<string, PluginState>>({});

  // カラム関連の状態（プラグインデータ用）
  const [pluginCsvColumns, setPluginCsvColumns] = useState<string[]>([]);
  const [pluginSelectedCommentColumn, setPluginSelectedCommentColumn] = useState<string>("");
  const [pluginSelectedAttributeColumns, setPluginSelectedAttributeColumns] = useState<string[]>([]);

  /**
   * 利用可能なプラグイン一覧を取得
   */
  useEffect(() => {
    const fetchPlugins = async () => {
      try {
        const pluginList = await getPlugins();
        setPlugins(pluginList);

        // 各プラグインの初期状態を設定
        const initialStates: Record<string, PluginState> = {};
        for (const plugin of pluginList) {
          initialStates[plugin.id] = {
            id: plugin.id,
            url: "",
            imported: false,
            loading: false,
            data: [],
            commentCount: 0,
          };
        }
        setPluginStates(initialStates);
      } catch (error) {
        console.error("Failed to fetch plugins:", error);
      } finally {
        setPluginsLoading(false);
      }
    };

    fetchPlugins();
  }, []);

  /**
   * 最適なカラムを選択する関数
   */
  const selectBestColumn = useCallback(
    (data: Record<string, unknown>[]) => {
      if (data.length === 0) return;
      const columns = Object.keys(data[0]);
      setPluginCsvColumns(columns);

      // スコアに基づいて最適なカラムを選択
      const bestColumn = getBestCommentColumn(data);
      if (bestColumn) {
        setPluginSelectedCommentColumn(bestColumn);
      }

      onDataLoaded(data.length);
    },
    [onDataLoaded],
  );

  /**
   * プラグインのURL変更ハンドラー
   */
  const handlePluginUrlChange = useCallback((pluginId: string, url: string) => {
    setPluginStates((prev) => ({
      ...prev,
      [pluginId]: {
        ...prev[pluginId],
        url,
      },
    }));
  }, []);

  /**
   * プラグインソースの検証
   */
  const handleValidateSource = useCallback(
    async (pluginId: string): Promise<boolean> => {
      const state = pluginStates[pluginId];
      if (!state?.url.trim()) {
        toaster.create({
          type: "error",
          title: "入力エラー",
          description: "URLを入力してください",
        });
        return false;
      }

      try {
        const result = await validatePluginSource(pluginId, state.url);
        if (!result.isValid) {
          toaster.create({
            type: "error",
            title: "検証エラー",
            description: result.error || "無効なURLです",
          });
          return false;
        }
        return true;
      } catch (error) {
        showErrorToast(toaster, error, "URL検証エラー");
        return false;
      }
    },
    [pluginStates],
  );

  /**
   * プラグインからデータをプレビュー
   */
  const handlePreviewPluginData = useCallback(
    async (pluginId: string) => {
      const state = pluginStates[pluginId];
      if (!state?.url.trim()) return;

      setPluginStates((prev) => ({
        ...prev,
        [pluginId]: { ...prev[pluginId], loading: true },
      }));

      try {
        const result = await previewPluginData(pluginId, state.url, 10);

        if (!result.success) {
          toaster.create({
            type: "error",
            title: "プレビューエラー",
            description: result.error || "データの取得に失敗しました",
          });
          return;
        }

        // プレビューデータをコメント形式に変換
        const comments = result.comments.map((c) => ({
          id: c["comment-id"] as string,
          comment: c["comment-body"] as string,
          source: c.source as string | null,
          url: c.url as string | null,
          ...Object.fromEntries(
            Object.entries(c)
              .filter(([k]) => k.startsWith("attribute_"))
              .map(([k, v]) => [k, v as string | null]),
          ),
        })) as SpreadsheetComment[];

        setPluginStates((prev) => ({
          ...prev,
          [pluginId]: {
            ...prev[pluginId],
            data: comments,
            commentCount: result.totalCount,
          },
        }));

        if (comments.length > 0) {
          selectBestColumn(comments as unknown as Record<string, unknown>[]);
        }

        toaster.create({
          type: "info",
          title: "プレビュー",
          description: `${result.totalCount} 件のコメントが見つかりました（${comments.length} 件を表示）`,
        });
      } catch (error) {
        showErrorToast(toaster, error, "プレビューエラー");
      } finally {
        setPluginStates((prev) => ({
          ...prev,
          [pluginId]: { ...prev[pluginId], loading: false },
        }));
      }
    },
    [pluginStates, selectBestColumn],
  );

  /**
   * プラグインからデータをインポート
   */
  const handleImportPluginData = useCallback(
    async (pluginId: string, fileName: string, maxResults = 1000) => {
      const state = pluginStates[pluginId];
      if (!state?.url.trim()) {
        toaster.create({
          type: "error",
          title: "入力エラー",
          description: "URLを入力してください",
        });
        return;
      }

      setPluginStates((prev) => ({
        ...prev,
        [pluginId]: { ...prev[pluginId], loading: true },
      }));

      try {
        const result = await importPluginData(pluginId, state.url, fileName, maxResults);

        if (!result.success) {
          toaster.create({
            type: "error",
            title: "インポートエラー",
            description: result.error || "データのインポートに失敗しました",
          });
          return;
        }

        // インポートされたコメントをコメント形式に変換
        const comments = result.comments.map((c) => ({
          id: c["comment-id"] as string,
          comment: c["comment-body"] as string,
          source: c.source as string | null,
          url: c.url as string | null,
          ...Object.fromEntries(
            Object.entries(c)
              .filter(([k]) => k.startsWith("attribute_"))
              .map(([k, v]) => [k, v as string | null]),
          ),
        })) as SpreadsheetComment[];

        setPluginStates((prev) => ({
          ...prev,
          [pluginId]: {
            ...prev[pluginId],
            imported: true,
            data: comments,
            commentCount: result.commentCount,
          },
        }));

        // カラム情報も更新
        if (comments.length > 0) {
          selectBestColumn(comments as unknown as Record<string, unknown>[]);
        }

        toaster.create({
          type: "success",
          title: "成功",
          description: `${result.commentCount} 件のコメントをインポートしました`,
        });

        onDataLoaded(result.commentCount);
      } catch (error) {
        showErrorToast(toaster, error, "インポートエラー");
      } finally {
        setPluginStates((prev) => ({
          ...prev,
          [pluginId]: { ...prev[pluginId], loading: false },
        }));
      }
    },
    [pluginStates, onDataLoaded, selectBestColumn],
  );

  /**
   * プラグインデータをクリア
   */
  const handleClearPluginData = useCallback((pluginId: string) => {
    setPluginStates((prev) => ({
      ...prev,
      [pluginId]: {
        ...prev[pluginId],
        url: "",
        imported: false,
        data: [],
        commentCount: 0,
      },
    }));
    setPluginCsvColumns([]);
    setPluginSelectedCommentColumn("");
    setPluginSelectedAttributeColumns([]);
  }, []);

  /**
   * 利用可能なプラグインのみを取得
   */
  const availablePlugins = plugins.filter((p) => p.isAvailable);

  /**
   * プラグインの状態を取得
   */
  const getPluginState = useCallback(
    (pluginId: string): PluginState | undefined => {
      return pluginStates[pluginId];
    },
    [pluginStates],
  );

  return {
    plugins,
    availablePlugins,
    pluginsLoading,
    pluginStates,
    pluginCsvColumns,
    pluginSelectedCommentColumn,
    pluginSelectedAttributeColumns,
    setPluginSelectedCommentColumn,
    setPluginSelectedAttributeColumns,
    getPluginState,
    handlePluginUrlChange,
    handleValidateSource,
    handlePreviewPluginData,
    handleImportPluginData,
    handleClearPluginData,
  };
}
