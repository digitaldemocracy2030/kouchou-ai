import { Button, Field, HStack, Input, Text } from "@chakra-ui/react";
import { ChevronRightIcon } from "lucide-react";
import React, { useState } from "react";
import type { ClusterSettings } from "../types";

export function ClusterSettingsSection({
  clusterLv1,
  clusterLv2,
  recommendedClusters,
  autoAdjusted,
  onLv1Change,
  onLv2Change,
}: {
  clusterLv1: number;
  clusterLv2: number;
  recommendedClusters: ClusterSettings | null;
  autoAdjusted: boolean;
  onLv1Change: (value: number) => void;
  onLv2Change: (value: number) => void;
}) {
  const [lv1Input, setLv1Input] = useState(clusterLv1.toString());
  const [lv2Input, setLv2Input] = useState(clusterLv2.toString());

  React.useEffect(() => {
    setLv1Input(clusterLv1.toString());
  }, [clusterLv1]);
  React.useEffect(() => {
    setLv2Input(clusterLv2.toString());
  }, [clusterLv2]);

  if (!recommendedClusters) return null;

  return (
    <Field.Root mt={4}>
      <Field.Label>意見グループ数設定</Field.Label>
      <HStack w={"100%"}>
        <Button onClick={() => onLv1Change(clusterLv1 - 1)} variant="outline">
          -
        </Button>
        <Input
          type="number"
          value={lv1Input}
          min={2}
          max={40}
          onChange={(e) => {
            setLv1Input(e.target.value);
          }}
          onBlur={(e) => {
            const v = Number(e.target.value);
            if (!Number.isNaN(v)) {
              onLv1Change(v);
            } else {
              setLv1Input(clusterLv1.toString());
            }
          }}
        />
        <Button onClick={() => onLv1Change(clusterLv1 + 1)} variant="outline">
          +
        </Button>
        <ChevronRightIcon width="100px" />
        <Button onClick={() => onLv2Change(clusterLv2 - 1)} variant="outline">
          -
        </Button>
        <Input
          type="number"
          value={lv2Input}
          min={2}
          max={1000}
          onChange={(e) => {
            setLv2Input(e.target.value);
          }}
          onBlur={(e) => {
            const v = Number(e.target.value);
            if (!Number.isNaN(v)) {
              onLv2Change(v);
            } else {
              setLv2Input(clusterLv2.toString());
            }
          }}
        />
        <Button onClick={() => onLv2Change(clusterLv2 + 1)} variant="outline">
          +
        </Button>
      </HStack>
      <Field.HelperText>
        階層ごとの意見グループ生成数です。初期値はコメント数に基づいた推奨意見グループ数です。
      </Field.HelperText>
      {autoAdjusted && (
        <Text color="orange.500" fontSize="sm" mt={2}>
          第2階層の意見グループ数が自動調整されました。第2階層の意見グループ数は第1階層の意見グループ数の2倍以上に設定してください。
        </Text>
      )}
    </Field.Root>
  );
}
