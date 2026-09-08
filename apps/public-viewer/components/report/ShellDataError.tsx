"use client";

import { Box, Heading, Text } from "@chakra-ui/react";

/**
 * shell ビルドで同梱データを読めなかったときの表示。
 *
 * 原因は API 接続ではなく配布物の組み立て（data/ 配下の欠落・破損）なので、
 * `ApiConnectionError` とは別の案内にする。
 */
export function ShellDataError({ url, message }: { url: string; message: string }) {
  return (
    <Box className="container" mt="8" maxW={"750px"} mx={"auto"} py={16}>
      <Heading fontSize={"xl"} mb={4}>
        レポートデータを読み込めませんでした
      </Heading>
      <Text mb={2}>
        配布物に同梱されたデータの取得に失敗しました。data/ 配下のファイルが揃っているか確認してください。
      </Text>
      <Text textStyle="body/sm" color="gray.600">
        取得先: {url}
      </Text>
      <Text textStyle="body/sm" color="gray.600">
        エラー: {message}
      </Text>
    </Box>
  );
}
