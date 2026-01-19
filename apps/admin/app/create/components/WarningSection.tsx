import { Alert, Stack } from "@chakra-ui/react";

/**
 * 警告メッセージセクションコンポーネント
 */
export function WarningSection() {
  return (
    <Stack gap="4" width="full">
      <Alert.Root status="warning">
        <Alert.Indicator />
        <Alert.Title>レポートの作成には数分から数十分程度の時間がかかります</Alert.Title>
      </Alert.Root>
      <Alert.Root status="warning">
        <Alert.Indicator />
        <Alert.Title>作成が完了したレポートが一覧画面に反映されるまで5分程度かかります</Alert.Title>
      </Alert.Root>
    </Stack>
  );
}
