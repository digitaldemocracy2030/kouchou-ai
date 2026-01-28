"use client";

import {
  DialogBackdrop,
  DialogBody,
  DialogCloseTrigger,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogRoot,
  DialogTitle,
} from "@/components/ui/dialog";
import { toaster } from "@/components/ui/toaster";
import type { Report } from "@/type";
import { Box, Button, Checkbox, Input, Portal, Text, Textarea, VStack } from "@chakra-ui/react";
import { useRouter } from "next/navigation";
import { type Dispatch, type FormEvent, type SetStateAction, useMemo, useState } from "react";
import { duplicateReport } from "./actions";

type Props = {
  report: Report;
  isOpen: boolean;
  setIsOpen: Dispatch<SetStateAction<boolean>>;
};

export function DuplicateReportDialog({ report, isOpen, setIsOpen }: Props) {
  const router = useRouter();
  const [newSlug, setNewSlug] = useState("");
  const [overviewPrompt, setOverviewPrompt] = useState("");
  const [reuseEnabled, setReuseEnabled] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const rerunSteps = useMemo(() => {
    if (!reuseEnabled) {
      return "extraction → embedding → clustering → overview";
    }
    return "overview";
  }, [reuseEnabled]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (isSubmitting) return;
    setIsSubmitting(true);

    const result = await duplicateReport(report.slug, {
      newSlug: newSlug.trim() || undefined,
      overviewPrompt: overviewPrompt.trim() || undefined,
      reuseEnabled,
    });

    if (result.success) {
      toaster.create({
        type: "success",
        title: "複製を開始しました",
        description: `新しいレポート: ${result.slug}`,
      });
      setIsOpen(false);
      setNewSlug("");
      setOverviewPrompt("");
      setReuseEnabled(true);
      router.refresh();
    } else {
      toaster.create({
        type: "error",
        title: "複製エラー",
        description: result.error || "複製に失敗しました",
      });
    }

    setIsSubmitting(false);
  }

  return (
    <DialogRoot placement="center" open={isOpen} onOpenChange={({ open }) => setIsOpen(open)}>
      <Portal>
        <DialogBackdrop />
        <DialogContent>
          <DialogCloseTrigger onClick={() => setIsOpen(false)} />
          <DialogHeader>
            <DialogTitle>レポートを複製</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit}>
            <DialogBody>
              <VStack gap={4} align="stretch">
                <Box>
                  <Text mb={2} fontWeight="bold">
                    新しいslug (任意)
                  </Text>
                  <Input
                    value={newSlug}
                    onChange={(event) => setNewSlug(event.target.value)}
                    placeholder={`${report.slug}-copy-YYYYMMDD`}
                  />
                  <Text fontSize="sm" color="gray.500" mt={1}>
                    空欄の場合は自動生成されます
                  </Text>
                </Box>
                <Box>
                  <Text mb={2} fontWeight="bold">
                    要約/解説プロンプト
                  </Text>
                  <Textarea
                    value={overviewPrompt}
                    onChange={(event) => setOverviewPrompt(event.target.value)}
                    placeholder="未入力の場合は元のプロンプトを再利用します"
                  />
                </Box>
                <Box>
                  <Checkbox
                    checked={reuseEnabled}
                    onCheckedChange={(details) => {
                      if (details.checked === "indeterminate") return;
                      setReuseEnabled(details.checked);
                    }}
                  >
                    再利用する
                  </Checkbox>
                </Box>
                <Box>
                  <Text fontWeight="bold" mb={1}>
                    再実行されるステップ
                  </Text>
                  <Text color="gray.600">{rerunSteps}</Text>
                  <Text color="gray.500" fontSize="sm" mt={1}>
                    複製時は overview を常に再生成します
                  </Text>
                </Box>
              </VStack>
            </DialogBody>
            <DialogFooter>
              <Button variant="outline" onClick={() => setIsOpen(false)}>
                キャンセル
              </Button>
              <Button ml={3} type="submit" loading={isSubmitting}>
                複製を開始
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Portal>
    </DialogRoot>
  );
}
