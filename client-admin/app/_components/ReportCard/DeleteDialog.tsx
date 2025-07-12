import { Button } from "@/components/ui/button";
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
import type { Report } from "@/type";
import { Center, Flex, Icon, Portal, Text, VStack } from "@chakra-ui/react";
import { FileText, Trash2 } from "lucide-react";
import type { Dispatch, SetStateAction } from "react";
import { reportDelete } from "./_actions/reportDelete";

type Props = {
  isOpen: boolean;
  setIsOpen: Dispatch<SetStateAction<boolean>>;
  report: Report;
};

export function DeleteDialog({ isOpen, setIsOpen, report }: Props) {
  return (
    <DialogRoot size="sm" placement="center" open={isOpen} modal={true} closeOnInteractOutside={true} trapFocus={true}>
      <Portal>
        <DialogBackdrop />
        <DialogContent>
          <DialogCloseTrigger onClick={() => setIsOpen(false)} />
          <DialogHeader justifyContent="center">
            <DialogTitle>
              <Icon color="font.error">
                <Trash2 />
              </Icon>
            </DialogTitle>
          </DialogHeader>
          <DialogBody>
            <VStack gap="3">
              <Text textStyle="body/lg/bold" textAlign="center">
                このレポートを
                <br />
                削除してよろしいですか？
              </Text>
              <Text textStyle="body/sm" textAlign="center">
                レポートは完全に削除されます。元に戻すことはできません。
              </Text>
              <Flex bg="bg.error" p="4" gap="3" alignItems="center">
                <Center w="48px" h="48px" flexShrink="0" bg="white" borderRadius="full">
                  <FileText />
                </Center>
                <Text textStyle="body/sm/bold">{report.title}</Text>
              </Flex>
            </VStack>
          </DialogBody>
          <DialogFooter justifyContent="center" pt="0" pb="8">
            <Button variant="tertiary" size="md" onClick={() => setIsOpen(false)}>
              キャンセル
            </Button>
            <Button
              variant="secondary"
              size="md"
              color="font.error"
              borderColor="border.error"
              onClick={async () => await reportDelete(report.slug)}
            >
              削除する
            </Button>
          </DialogFooter>
        </DialogContent>
      </Portal>
    </DialogRoot>
  );
}
