import { useCallback, useState } from "react";
import type { ClusterSettings } from "../types";

// カスタムフック: 意見グループ設定の管理
export function useClusterSettings(initialLv1 = 5, initialLv2 = 50) {
  const [clusterLv1, setClusterLv1] = useState<number>(initialLv1);
  const [clusterLv2, setClusterLv2] = useState<number>(initialLv2);
  const [recommendedClusters, setRecommendedClusters] = useState<ClusterSettings | null>(null);
  const [autoAdjusted, setAutoAdjusted] = useState<boolean>(false);

  // コメント数から意見グループ数を計算
  const calculateRecommendedClusters = useCallback((commentCount: number) => {
    const lv1 = Math.max(2, Math.min(10, Math.round(Math.cbrt(commentCount))));
    const lv2 = Math.max(2, Math.min(1000, Math.round(lv1 * lv1)));
    return { lv1, lv2 };
  }, []);

  const setRecommended = useCallback(
    (commentCount: number) => {
      const recommended = calculateRecommendedClusters(commentCount);
      setRecommendedClusters(recommended);
      setClusterLv1(recommended.lv1);
      setClusterLv2(recommended.lv2);
      return recommended;
    },
    [calculateRecommendedClusters],
  );

  const handleLv1Change = useCallback(
    (newValue: number) => {
      const limitedValue = Math.max(2, Math.min(40, newValue));
      setClusterLv1(limitedValue);

      // 第一階層の意見グループ数 * 2 > 第二階層の意見グループ数の場合のみ、第二階層の値を更新
      const newClusterLv2 = limitedValue * 2;
      if (newClusterLv2 > clusterLv2) {
        setClusterLv2(newClusterLv2);
        setAutoAdjusted(true);

        // 推奨意見グループ数表示を更新（nullでない場合のみ）
        if (recommendedClusters) {
          setRecommendedClusters({
            lv1: limitedValue,
            lv2: newClusterLv2,
          });
        }
      } else if (recommendedClusters) {
        setRecommendedClusters({
          lv1: limitedValue,
          lv2: clusterLv2,
        });
      }
    },
    [clusterLv2, recommendedClusters],
  );

  const handleLv2Change = useCallback(
    (newValue: number) => {
      let limitedValue = Math.max(2, Math.min(1000, newValue));

      // 第二階層の値が第一階層の値の2倍未満の場合は自動調整
      if (limitedValue < clusterLv1 * 2) {
        limitedValue = clusterLv1 * 2;
        setAutoAdjusted(true);
      } else {
        setAutoAdjusted(false);
      }

      setClusterLv2(limitedValue);

      // 推奨意見グループ数表示を更新（nullでない場合のみ）
      if (recommendedClusters) {
        setRecommendedClusters({
          lv1: recommendedClusters.lv1,
          lv2: limitedValue,
        });
      }
    },
    [clusterLv1, recommendedClusters],
  );

  // リセット
  const resetClusterSettings = useCallback(() => {
    setClusterLv1(initialLv1);
    setClusterLv2(initialLv2);
    setRecommendedClusters(null);
    setAutoAdjusted(false);
  }, [initialLv1, initialLv2]);

  return {
    clusterLv1,
    clusterLv2,
    recommendedClusters,
    autoAdjusted,
    calculateRecommendedClusters,
    setRecommended,
    handleLv1Change,
    handleLv2Change,
    resetClusterSettings,
  };
}
