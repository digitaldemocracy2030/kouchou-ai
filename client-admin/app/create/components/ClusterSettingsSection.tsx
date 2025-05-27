import { Checkbox } from "@/components/ui/checkbox";
import { Field, HStack, Input, Text } from "@chakra-ui/react";
import type { Warning } from "../hooks/useClusterSettings";
import type { ClusterSettings } from "../types";

export function ClusterSettingsSection({
  clusterLv1,
  clusterLv2,
  recommendedClusters,
  autoAdjusted,
  onLv1Change,
  onLv2Change,
  autoClusterEnabled,
  clusterLv1Min,
  clusterLv1Max,
  clusterLv2Min,
  clusterLv2Max,
  onAutoClusterToggle,
  onLv1MinChange,
  onLv1MaxChange,
  onLv2MinChange,
  onLv2MaxChange,
  manualWarnings,
}: {
  clusterLv1: number;
  clusterLv2: number;
  recommendedClusters: ClusterSettings | null;
  autoAdjusted: boolean;
  onLv1Change: (value: number) => void;
  onLv2Change: (value: number) => void;
  autoClusterEnabled: boolean;
  clusterLv1Min: number;
  clusterLv1Max: number;
  clusterLv2Min: number;
  clusterLv2Max: number;
  onAutoClusterToggle: (value: boolean) => void;
  onLv1MinChange: (value: number) => void;
  onLv1MaxChange: (value: number) => void;
  onLv2MinChange: (value: number) => void;
  onLv2MaxChange: (value: number) => void;
  manualWarnings: Warning[];
}) {
  if (!recommendedClusters) return null;

  const lv1HasWarning = manualWarnings.some((w) => w.field === "lv1");
  const lv2HasWarning = manualWarnings.some((w) => w.field === "lv2");

  return (
    <Field.Root mt={4}>
      <HStack justify="space-between" w="100%" align="center">
        <Field.Label>意見グループ数設定</Field.Label>
        <Checkbox checked={autoClusterEnabled} onCheckedChange={({ checked }) => onAutoClusterToggle(checked === true)}>
          グループ数を自動で決定する（ベータ版機能）
        </Checkbox>
      </HStack>

      <HStack mt={3} flexWrap="wrap" w="100%" align="center">
        <Text fontSize="sm" w="100px">
          第一階層
        </Text>
        {autoClusterEnabled ? (
          <>
            <Input
              type="number"
              value={clusterLv1Min.toString()}
              onChange={(e) => onLv1MinChange(Number(e.target.value))}
              size="sm"
              w="81px"
            />
            <Text fontSize="sm" mx={1}>
              ～
            </Text>
            <Input
              type="number"
              value={clusterLv1Max.toString()}
              onChange={(e) => onLv1MaxChange(Number(e.target.value))}
              size="sm"
              w="81px"
            />
            <Text fontSize="sm" mx={3} w="40px" textAlign="center">
              ▶
            </Text>
            <Text fontSize="sm" w="100px">
              第二階層
            </Text>
            <Input
              type="number"
              value={clusterLv2Min.toString()}
              onChange={(e) => onLv2MinChange(Number(e.target.value))}
              size="sm"
              w="81px"
            />
            <Text fontSize="sm" mx={1}>
              ～
            </Text>
            <Input
              type="number"
              value={clusterLv2Max.toString()}
              onChange={(e) => onLv2MaxChange(Number(e.target.value))}
              size="sm"
              w="81px"
            />
          </>
        ) : (
          <>
            <Input
              type="number"
              value={clusterLv1.toString()}
              onChange={(e) => onLv1Change(Number(e.target.value))}
              min={clusterLv1Min}
              max={clusterLv1Max}
              size="sm"
              w="200px"
            />
            <Text fontSize="sm" mx={3} w="40px" textAlign="center">
              ▶
            </Text>
            <Text fontSize="sm" w="100px">
              第二階層
            </Text>
            <Input
              type="number"
              value={clusterLv2.toString()}
              onChange={(e) => onLv2Change(Number(e.target.value))}
              min={clusterLv2Min}
              max={clusterLv2Max}
              size="sm"
              w="200px"
            />
          </>
        )}
      </HStack>

      {manualWarnings.map((w) => (
        <Text key={`${w.field}-${w.message}`} fontSize="sm" color="orange.500">
          {w.message}
        </Text>
      ))}

      {autoClusterEnabled ? (
        <Field.HelperText mt={2}>
          階層ごとの意見グループ生成数を「下限 ～ 上限」の範囲で自動的に評価し、最適な数を決定します。
        </Field.HelperText>
      ) : (
        <>
          <Field.HelperText mt={2}>
            階層ごとの意見グループ生成数を手動で設定します。初期値はコメント数に基づいた推奨意見グループ数です。
          </Field.HelperText>
        </>
      )}
    </Field.Root>
  );
}
