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
              広聴AIは、デジタル民主主義2030プロジェクトから生まれたオープンソースソフトウェアを、無保証で提供しています。ソフトウェアの提供元は、個々の稼働環境の運用や、生成されたレポートの内容について責任を負いません。
              <br />
              このレポートの内容・入力データ・問いの立て方は、レポートの発行者に帰属します。レポート内容に関する質問やご意見は、レポート発行責任者へお問い合わせください。稼働しているサービスの運用（可用性やデータの取り扱いなど）については、そのサービスの運営者が責任を負います。
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
