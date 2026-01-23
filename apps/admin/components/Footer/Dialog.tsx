"use client";

import { Portal, Text } from "@chakra-ui/react";
import { useRef } from "react";
import { Button } from "../ui/button";
import {
  DialogActionTrigger,
  DialogBody,
  DialogCloseTrigger,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogRoot,
  DialogTitle,
  DialogTrigger,
} from "../ui/dialog";

export const Dialog = () => {
  const ref = useRef<HTMLButtonElement>(null);
  return (
    <DialogRoot size="sm" initialFocusEl={() => ref.current}>
      <DialogTrigger asChild>
        <Button variant="ghost">免責</Button>
      </DialogTrigger>
      <Portal>
        <DialogContent
          mx="4"
          color="gray.800"
          bg="linear-gradient(216.39deg, #FCFFDB -0.01%, #F0FDF4 24.99%, #ECFEFF 35%, #FFFFFF 50%);
"
        >
          <DialogHeader pt={{ base: "6", md: "8" }} justifyContent="center">
            <DialogTitle>免責</DialogTitle>
          </DialogHeader>
          <DialogBody px={{ base: "6", md: "8" }}>
            <Text textStyle="body/md">
              このレポート内容に関する質問や意見はレポート発行責任者へお問い合わせください。
              <br />
              大規模言語モデル（LLM）にはバイアスがあり、信頼性の低い結果を生成することが知られています。私たちはこれらの問題を軽減する方法に積極的に取り組んでいますが、現段階ではいかなる保証も提供することはできません。特に重要な決定を下す際は、本アプリの出力結果のみに依存せず、必ず内容を検証してください。
            </Text>
          </DialogBody>
          <DialogCloseTrigger />
          <DialogFooter pb={{ base: "6", md: "8" }} justifyContent="center">
            <DialogActionTrigger asChild>
              <Button ref={ref} variant="tertiary" size="md">
                閉じる
              </Button>
            </DialogActionTrigger>
          </DialogFooter>
        </DialogContent>
      </Portal>
    </DialogRoot>
  );
};
