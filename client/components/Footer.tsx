"use client";

import type { Meta } from "@/type";
import { Box, type ButtonProps as ChakraButtonProps, Flex, Link, Text, Button as _Button } from "@chakra-ui/react";
import { ArrowUpRight } from "lucide-react";
import Image from "next/image";
import { forwardRef, useRef, type ReactNode } from "react";
import { GitHubIcon, NoteIcon, SlackIcon, XIcon } from "./icons/MediaIcons";
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
} from "./ui/dialog";

type Props = {
  meta: Meta;
};

const Dialog = ({ title, trigger, children }: { title: string; trigger: ReactNode; children: ReactNode }) => {
  const ref = useRef<HTMLButtonElement>(null);
  return (
    <DialogRoot size="sm" initialFocusEl={() => ref.current}>
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent
        mx="4"
        color="gray.800"
        bg="linear-gradient(216.39deg, #FCFFDB -0.01%, #F0FDF4 24.99%, #ECFEFF 35%, #FFFFFF 50%);
"
      >
        <DialogHeader pt={{ base: "6", md: "8" }} justifyContent="center">
          <DialogTitle>{title}</DialogTitle>
        </DialogHeader>
        <DialogBody px={{ base: "6", md: "8" }}>
          <Text fontSize="sm" lineHeight="2">
            {children}
          </Text>
        </DialogBody>
        <DialogCloseTrigger />
        <DialogFooter pb={{ base: "6", md: "8" }} justifyContent="center">
          <DialogActionTrigger asChild>
            <Button ref={ref} size="md" borderColor="gray.300">
              閉じる
            </Button>
          </DialogActionTrigger>
        </DialogFooter>
      </DialogContent>
    </DialogRoot>
  );
};

const Button = forwardRef<HTMLButtonElement, ChakraButtonProps>(({ children, ...props }, ref) => {
  return (
    <_Button
      variant="outline"
      rounded="full"
      size="xs"
      fontWeight="bold"
      px="5"
      borderColor="gray.800"
      gap="2"
      _icon={{
        width: "16px",
        height: "16px",
      }}
      ref={ref}
      {...props}
    >
      {children}
    </_Button>
  );
});

export function Footer({ meta }: Props) {
  return (
    <Box as="footer" fontSize="xs" color="gray.800" lineHeight="2">
      <Box
        bg="url('/images/footer-bg.webp')"
        bgSize="cover"
        bgPos="center"
        py={{ base: "6", md: "10" }}
        px={{ base: "6", md: "12" }}
      >
        <Flex
          bg="white"
          py="8"
          px="8"
          borderRadius="3xl"
          maxW="1024px"
          mx="auto"
          flexDirection={{ base: "column", lg: "row" }}
          alignItems={{ base: "center", lg: "flex-end" }}
          gap="8"
        >
          <Image
            src="/images/kouchouai-logo.svg"
            alt="広聴AI すべての声が社会を動かす力になる。"
            width={256}
            height={102}
          />
          <Flex flexDirection="column" gap={{ base: "4" }}>
            <Text>
              広聴AIは、デジタル民主主義2030プロジェクトから生まれたオープンソース（OSS）アプリケーションです。
              <Box as="br" display={{ base: "none", lg: "inline" }} />
              本ページは、そのOSS成果物を活用して構築されています。
            </Text>
            <Flex gap="3">
              <Button asChild>
                <a href="https://dd2030.org/kouchou-ai" target="_blank" rel="noopener noreferrer">
                  広聴AIについて
                  <ArrowUpRight />
                </a>
              </Button>
              <Dialog title="謝辞" trigger={<Button>謝辞</Button>}>
                広聴AIは{" "}
                <Link
                  href="https://ai.objectives.institute/"
                  target="_blank"
                  rel="noopener noreferrer"
                  color="blue.500"
                >
                  AI Objectives Institute
                </Link>{" "}
                が開発した{" "}
                <Link
                  href="https://github.com/AIObjectives/talk-to-the-city-reports"
                  target="_blank"
                  rel="noopener noreferrer"
                  color="blue.500"
                >
                  Talk to the City
                </Link>{" "}
                を参考に開発されています。ライセンスに基づいてソースコードを一部活用し、機能追加や改善を実施しています。
              </Dialog>
            </Flex>
          </Flex>
        </Flex>
      </Box>
      <Box bg="#F1F6F8" py={{ base: "6", md: "10" }} px={{ base: "6", md: "12" }} mx="auto">
        <Flex
          bg="white"
          py="8"
          px="8"
          borderRadius="3xl"
          maxW="1024px"
          mx="auto"
          flexDirection={{ base: "column", lg: "row" }}
          alignItems={{ base: "center" }}
          gap="8"
        >
          <Image src="/images/dd2030-logo-full.svg" alt="デジタル民主主義2030" width={256} height={80} />
          <Flex flexDirection="column" gap="4">
            <Text>
              2030年には、情報技術により民主主義のあり方はアップデートされており、一人ひとりの声が政治・行政に届き、適切に合意形成・政策反映されていくような社会が当たり前になる、──そんな未来を目指して立ち上げられたのがデジタル民主主義2030プロジェクトです。
            </Text>
            <Flex gap="3" flexWrap="wrap">
              <Button asChild>
                <a href="https://dd2030.org" rel="noopener noreferrer" target="_blank">
                  プロジェクトサイト
                  <ArrowUpRight />
                </a>
              </Button>
              <Button asChild>
                <a href="https://x.com/dd2030jp" rel="noopener noreferrer" target="_blank">
                  <XIcon />
                </a>
              </Button>
              <Button asChild _icon={{ width: "42px", height: "12px" }}>
                <a href="https://note.com/dd2030" rel="noopener noreferrer" target="_blank">
                  <NoteIcon />
                </a>
              </Button>
              <Button asChild>
                <a href="https://dd2030.slack.com" rel="noopener noreferrer" target="_blank">
                  <SlackIcon />
                  Slack
                </a>
              </Button>
              <Button asChild>
                <a href="https://github.com/digitaldemocracy2030" rel="noopener noreferrer" target="_blank">
                  <GitHubIcon />
                  GitHub
                </a>
              </Button>
            </Flex>
          </Flex>
        </Flex>
      </Box>
      <Box bg="white" py={{ base: "6", lg: "4" }} px={{ base: "6", md: "12" }} textAlign="center">
        <Flex
          maxW="1024px"
          mx="auto"
          justifyContent={{ lg: "space-between" }}
          alignItems={{ base: "center" }}
          flexDirection={{ base: "column-reverse", lg: "row" }}
          gap={{ base: "4" }}
        >
          <Text display="flex" color="gray.500" fontSize="xs">
            © 2025 デジタル民主主義2030
            <Box as="span" mx="0.4em" display={{ base: "none", lg: "inline" }}>
              |
            </Box>
            <Box as="br" display={{ base: "inline", lg: "none" }} />
            レポート内容はレポーターに帰属します
          </Text>
          <Flex gap="0" alignItems="center" color="gray.800">
            {meta.termsLink && (
              <Button variant="ghost" border="none" asChild>
                <a href={meta.termsLink} target="_blank" rel="noopener noreferrer">
                  <Text fontWeight="bold" fontSize="xs">
                    利用規約
                  </Text>
                </a>
              </Button>
            )}
            <Dialog
              title="免責"
              trigger={
                <Button variant="ghost" border="none">
                  免責
                </Button>
              }
            >
              このレポート内容に関する質問や意見はレポート発行責任者へお問い合わせください。
              <br />
              大規模言語モデル（LLM）にはバイアスがあり、信頼性の低い結果を生成することが知られています。私たちはこれらの問題を軽減する方法に積極的に取り組んでいますが、現段階ではいかなる保証も提供することはできません。特に重要な決定を下す際は、本アプリの出力結果のみに依存せず、必ず内容を検証してください。
            </Dialog>
          </Flex>
        </Flex>
      </Box>
    </Box>
  );
}
