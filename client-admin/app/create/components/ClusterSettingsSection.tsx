import { Checkbox } from "@/components/ui/checkbox";
import { Box, Button, Field, HStack, Input, Text } from "@chakra-ui/react";
import type { ClusterSettings } from "../types";

export function ClusterSettingsSection({
  clusterLv1,
  clusterLv2,
  recommendedClusters,
  autoAdjusted,
  onLv1Change,
  onLv2Change,
  autoClusterEnabled,
  clusterTopMax,
  clusterBottomMax,
  onAutoClusterToggle,
  onTopMaxChange,
  onBottomMaxChange,
}: {
  clusterLv1: number;
  clusterLv2: number;
  recommendedClusters: ClusterSettings | null;
  autoAdjusted: boolean;
  onLv1Change: (value: number) => void;
  onLv2Change: (value: number) => void;
  autoClusterEnabled: boolean;
  clusterTopMax: number;
  clusterBottomMax: number;
  onAutoClusterToggle: (value: boolean) => void;
  onTopMaxChange: (value: number) => void;
  onBottomMaxChange: (value: number) => void;
}) {
  if (!recommendedClusters) return null;

  return (
    <Field.Root mt={4}>
      <HStack justify="space-between" w="100%" align="center">
        <Field.Label>意見グループ数設定</Field.Label>
        <Checkbox checked={autoClusterEnabled} onCheckedChange={({ checked }) => onAutoClusterToggle(checked === true)}>
          グループ数を自動で決定する
        </Checkbox>
      </HStack>

      <HStack mt={3} flexWrap="wrap" w="100%">
        {autoClusterEnabled ? (
          <>
            <Text fontSize="sm" w="80px">
              2～
            </Text>
            <Button onClick={() => onTopMaxChange(clusterTopMax - 1)} variant="outline" size="sm">
              -
            </Button>
            <Input
              type="number"
              value={clusterTopMax.toString()}
              min={2}
              max={40}
              onChange={(e) => {
                const v = Number(e.target.value);
                if (!Number.isNaN(v)) onTopMaxChange(v);
              }}
              size="sm"
              w="100px"
            />
            <Button onClick={() => onTopMaxChange(clusterTopMax + 1)} variant="outline" size="sm">
              +
            </Button>

            <Text fontSize="sm" mx={3} w="40px" textAlign="center">
              ▶
            </Text>

            <Text fontSize="sm" w="60px">
              {clusterTopMax + 1} ～
            </Text>
            <Button onClick={() => onBottomMaxChange(clusterBottomMax - 1)} variant="outline" size="sm">
              -
            </Button>
            <Input
              type="number"
              value={clusterBottomMax.toString()}
              min={clusterTopMax + 1}
              max={1000}
              onChange={(e) => {
                const v = Number(e.target.value);
                if (!Number.isNaN(v)) onBottomMaxChange(v);
              }}
              size="sm"
              w="100px"
            />
            <Button onClick={() => onBottomMaxChange(clusterBottomMax + 1)} variant="outline" size="sm">
              +
            </Button>
          </>
        ) : (
          <>
            <Box w="80px" /> {/* ▶位置調整のために空幅 */}
            <Button onClick={() => onLv1Change(clusterLv1 - 1)} variant="outline" size="sm">
              -
            </Button>
            <Input
              type="number"
              value={clusterLv1.toString()}
              min={2}
              max={40}
              onChange={(e) => {
                const v = Number(e.target.value);
                if (!Number.isNaN(v)) onLv1Change(v);
              }}
              size="sm"
              w="100px"
            />
            <Button onClick={() => onLv1Change(clusterLv1 + 1)} variant="outline" size="sm">
              +
            </Button>
            <Text fontSize="sm" mx={3} w="40px" textAlign="center">
              ▶
            </Text>
            <Button onClick={() => onLv2Change(clusterLv2 - 1)} variant="outline" size="sm">
              -
            </Button>
            <Input
              type="number"
              value={clusterLv2.toString()}
              min={2}
              max={1000}
              onChange={(e) => {
                const v = Number(e.target.value);
                if (!Number.isNaN(v)) onLv2Change(v);
              }}
              size="sm"
              w="100px"
            />
            <Button onClick={() => onLv2Change(clusterLv2 + 1)} variant="outline" size="sm">
              +
            </Button>
          </>
        )}
      </HStack>

      {autoClusterEnabled ? (
        <Field.HelperText mt={2}>自動モードでは、上限範囲内で複数のクラスタ数を評価します。</Field.HelperText>
      ) : (
        <>
          <Field.HelperText mt={2}>
            階層ごとの意見グループ生成数を手動で設定します。初期値はコメント数に基づいた推奨意見グループ数です。
          </Field.HelperText>
          {autoAdjusted && (
            <Text color="orange.500" fontSize="sm" mt={2}>
              第2階層の意見グループ数が自動調整されました。第2階層の意見グループ数は第1階層の意見グループ数の2倍以上に設定してください。
            </Text>
          )}
        </>
      )}
    </Field.Root>
  );
}
