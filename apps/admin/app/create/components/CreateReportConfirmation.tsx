"use client";

import { DialogBody, DialogContent, DialogFooter, DialogHeader, DialogRoot, DialogTitle } from "@/components/ui/dialog";
import { Box, Button, HStack, Text, VStack } from "@chakra-ui/react";
import { useRef, useState } from "react";
import type { createReport } from "../api/createReport";
import { verifyApiKey } from "./EnvironmentCheckDialog/verifyApiKey";

export type PreparedReport = {
  request: Parameters<typeof createReport>[0];
  commentColumn: string;
  attributeColumns: string[];
};

type CheckStatus =
  | "unchecked"
  | "checking"
  | "ok"
  | "authentication_error"
  | "insufficient_quota"
  | "rate_limit_error"
  | "unknown_error";
const checkMessages: Record<CheckStatus, string> = {
  unchecked: "未確認",
  checking: "確認中…",
  ok: "OK（検証用モデルで接続確認済み）",
  authentication_error: "認証エラー：APIキーの設定・有効期限を確認してください。",
  insufficient_quota: "残高不足 / quota不足：プロバイダーの課金設定・利用上限を確認してください。",
  rate_limit_error: "rate limit：時間をおいて再度お試しください。",
  unknown_error: "不明なエラー：接続先やAPI設定を確認してください。",
};

export function CreateReportConfirmation({
  prepared,
  loading,
  onCancel,
  onConfirm,
}: {
  prepared: PreparedReport;
  loading: boolean;
  onCancel: () => void;
  onConfirm: () => void;
}) {
  const titleRef = useRef<HTMLHeadingElement>(null);
  const [check, setCheck] = useState<CheckStatus>("unchecked");
  const request = prepared.request;
  const nonEmptyCount = request.comments.filter((row) => typeof row.comment === "string" && row.comment.trim()).length;
  const inputName =
    request.inputType === "file" ? "CSV" : request.inputType === "spreadsheet" ? "Spreadsheet" : request.inputType;
  const busy = loading || check === "checking";
  const checkFailed = !["unchecked", "checking", "ok"].includes(check);

  const verify = async () => {
    setCheck("checking");
    try {
      const response = await verifyApiKey(request.provider, request.userApiKey);
      if (response.result?.success && !response.error) setCheck("ok");
      else setCheck(response.result?.error_type || "unknown_error");
    } catch {
      setCheck("unknown_error");
    }
  };

  return (
    <DialogRoot
      open
      initialFocusEl={() => titleRef.current}
      size="lg"
      placement="center"
      scrollBehavior="inside"
      onOpenChange={({ open }) => {
        if (!open && !loading) onCancel();
      }}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle ref={titleRef} tabIndex={-1}>
            作成前の確認
          </DialogTitle>
        </DialogHeader>
        <DialogBody overflowWrap="anywhere">
          <VStack align="stretch" gap="5">
            <Box>
              <Text fontWeight="bold">{request.question}</Text>
              <Text>入力元：{inputName}</Text>
              <Text>コメント列：{prepared.commentColumn}</Text>
              <Text>
                コメント件数：{request.comments.length.toLocaleString()}件（非空：{nonEmptyCount.toLocaleString()}件）
              </Text>
              <Text>属性列：{prepared.attributeColumns.join("、") || "なし"}</Text>
              <Text>
                クラスタ数：第1階層 {request.cluster[0]} / 第2階層 {request.cluster[1]}
              </Text>
              <Text>
                AI：{request.provider} / {request.provider === "azure" ? "サーバー設定を使用" : request.model}
              </Text>
              <Text>並列数：{request.workers}</Text>
            </Box>
            {nonEmptyCount < request.cluster[1] && (
              <Box role="alert" p="3" bg="orange.50" borderRadius="md">
                <Text>
                  非空コメント数が第2階層のクラスタ数を下回っています。処理中にエラーになる可能性があります。設定を戻って確認してください。
                </Text>
              </Box>
            )}
            {nonEmptyCount < request.comments.length && (
              <Text role="alert" color="orange.700">
                空のコメントが{request.comments.length - nonEmptyCount}
                件あります。コメント列と入力内容を確認してください。
              </Text>
            )}
            <Box borderWidth="1px" borderRadius="md" p="4">
              <Text fontWeight="bold">API接続チェック</Text>
              <Text as="output" display="block" aria-live="polite" mt="2">
                {checkMessages[check]}
              </Text>
              {request.provider === "local" ? (
                <Text mt="2" fontSize="sm">
                  この画面では選択したローカル接続先・モデルの接続確認に未対応です。
                </Text>
              ) : (
                <>
                  <Text mt="2" fontSize="sm">
                    接続チェックにはAPI利用料がかかる場合があります。検証用モデルでの確認であり、選択モデルの実行や必要な残高を保証するものではありません。
                  </Text>
                  <Button mt="3" variant="outline" onClick={verify} disabled={busy}>
                    API接続を確認する
                  </Button>
                </>
              )}
            </Box>
            <HStack gap="6" flexWrap="wrap">
              <Text>費用：目安なし</Text>
              <Text>時間：目安なし</Text>
            </HStack>
            <Text fontSize="sm">有料のAIプロバイダーでは作成する度にAPI利用料がかかります。</Text>
          </VStack>
        </DialogBody>
        <DialogFooter flexWrap="wrap">
          <Button variant="outline" onClick={onCancel} disabled={loading}>
            設定に戻る
          </Button>
          <Button onClick={onConfirm} loading={loading} disabled={busy || nonEmptyCount === 0}>
            {check === "ok"
              ? "この内容で作成を開始"
              : checkFailed
                ? "エラーを確認して作成を開始"
                : "未確認のまま作成を開始"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </DialogRoot>
  );
}
