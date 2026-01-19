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
import { Box, Button, Input, Portal, Text, Textarea, VStack } from "@chakra-ui/react";
import { useRouter } from "next/navigation";
import type { Dispatch, FormEvent, SetStateAction } from "react";
import { updateReportConfig } from "./actions";

type Props = {
  isEditDialogOpen: boolean;
  setIsEditDialogOpen: Dispatch<SetStateAction<boolean>>;
  report: Report;
};

export function ReportEditDialog({ isEditDialogOpen, setIsEditDialogOpen, report }: Props) {
  const router = useRouter();

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    const formData = new FormData(event.currentTarget);
    const result = await updateReportConfig(report.slug, formData);

    if (result.success) {
      router.refresh();

      toaster.create({
        type: "success",
        title: "更新完了",
        description: "レポート情報が更新されました",
      });

      setIsEditDialogOpen(false);
    } else {
      toaster.create({
        type: "error",
        title: "更新エラー",
        description: result.error || "メタデータの更新に失敗しました",
      });
    }
  }

  return (
    <DialogRoot placement="center" open={isEditDialogOpen} onOpenChange={({ open }) => setIsEditDialogOpen(open)}>
      <Portal>
        <DialogBackdrop />
        <DialogContent>
          <DialogCloseTrigger />
          <DialogHeader>
            <DialogTitle>レポートを編集</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit}>
            <DialogBody>
              <VStack gap={4} align="stretch">
                <Box>
                  <Text mb={2} fontWeight="bold">
                    タイトル
                  </Text>
                  <Input name="question" defaultValue={report.title} placeholder="レポートのタイトルを入力" />
                </Box>
                <Box>
                  <Text mb={2} fontWeight="bold">
                    調査概要
                  </Text>
                  <Textarea name="intro" defaultValue={report.description || ""} placeholder="調査の概要を入力" />
                </Box>
              </VStack>
            </DialogBody>
            <DialogFooter>
              <Button variant="outline" onClick={() => setIsEditDialogOpen(false)}>
                キャンセル
              </Button>
              <Button ml={3} type="submit">
                保存
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Portal>
    </DialogRoot>
  );
}
