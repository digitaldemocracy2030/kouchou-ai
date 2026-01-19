"use client";

import { getClusterNum } from "@/app/utils/cluster-num";
import {
  DrawerBackdrop,
  DrawerBody,
  DrawerContent,
  DrawerFooter,
  DrawerHeader,
  DrawerRoot,
  DrawerTitle,
} from "@/components/ui/drawer";
import {
  TimelineConnector,
  TimelineContent,
  TimelineDescription,
  TimelineItem,
  TimelineRoot,
  TimelineTitle,
} from "@/components/ui/timeline";
import { Tooltip } from "@/components/ui/tooltip";
import type { Result } from "@/type";
import {
  Box,
  Button,
  Flex,
  HStack,
  Heading,
  Icon,
  Presence,
  Separator,
  Text,
  VStack,
  useDisclosure,
} from "@chakra-ui/react";
import {
  ChevronRightIcon,
  CircleArrowDownIcon,
  ClipboardCheckIcon,
  MessageCircleWarningIcon,
  MessagesSquareIcon,
} from "lucide-react";
import { useState } from "react";

type ReportProps = {
  result: Result;
};

export function Analysis({ result }: ReportProps) {
  const [selectedData, setSelectedData] = useState<{
    title: string;
    body: string;
  } | null>(null);
  const clusterNum = getClusterNum(result);
  const { open, onToggle } = useDisclosure();

  return (
    <Box mx={"auto"} maxW={"750px"} mb={12} cursor={"default"}>
      <Separator mt={20} mb={12} />
      <Heading textAlign={"center"} fontSize={"xl"} mb={5}>
        分析の概要
      </Heading>
      <HStack mb={5} justify={"center"}>
        <Tooltip
          content={
            "全てのコメントをAIで分析し、意見が含まれるコメントを抽出します。意見が含まれないコメントや、議題と関係のないコメントは除外されます。"
          }
          openDelay={0}
          closeDelay={0}
        >
          <VStack gap={0} w={"200px"}>
            <Icon mb={2}>
              <MessageCircleWarningIcon size={"30px"} />
            </Icon>
            <Text className={"headingColor"} fontSize={"3xl"} fontWeight={"bold"} lineHeight={1} mb={1}>
              {result.comment_num.toLocaleString()}
            </Text>
            <Text fontSize={"xs"}>コメント数</Text>
          </VStack>
        </Tooltip>
        <ChevronRightIcon />
        <Tooltip
          content={
            "抽出したコメントをAIで分析し、様々な意見を抽出します。複数の意見が混ざったコメントなども適切に分離します。"
          }
          openDelay={0}
          closeDelay={0}
        >
          <VStack gap={0} w={"200px"}>
            <Icon mb={2}>
              <MessagesSquareIcon size={"30px"} />
            </Icon>
            <Text className={"headingColor"} fontSize={"3xl"} fontWeight={"bold"} lineHeight={1} mb={1}>
              {result.arguments.length.toLocaleString()}
            </Text>
            <Text fontSize={"xs"}>抽出した意見数</Text>
          </VStack>
        </Tooltip>
        <ChevronRightIcon />
        <Tooltip
          content={
            "抽出した意見をAIで分析し、近しい意見を一つの意見グループに分類します。意見グループごとの意見を要約し、大量の意見を見える化します。"
          }
          openDelay={0}
          closeDelay={0}
        >
          <VStack gap={0} w={"200px"}>
            <Icon mb={2}>
              <ClipboardCheckIcon size={"30px"} />
            </Icon>
            <HStack gap={1} alignItems={"center"}>
              <Text className={"headingColor"} fontSize={"3xl"} fontWeight={"bold"} lineHeight={1} mb={1}>
                {clusterNum["1"].toLocaleString()}
              </Text>
              <Text fontSize={"md"}>→</Text>
              <Text className={"headingColor"} fontSize={"3xl"} fontWeight={"bold"} lineHeight={1} mb={1}>
                {clusterNum["2"].toLocaleString()}
              </Text>
            </HStack>
            <Text fontSize={"xs"}>集約した意見グループ数</Text>
          </VStack>
        </Tooltip>
      </HStack>
      <Text mb={5}>{result.config.intro}</Text>
      <Box>
        <Flex align={"center"} mb={5}>
          <Heading fontSize={"md"}>分析手順</Heading>
          <Button variant={"outline"} size={"sm"} ml={2} onClick={onToggle}>
            {open ? "非表示" : "表示"}
          </Button>
        </Flex>
        <Presence present={open}>
          <TimelineRoot size={"lg"}>
            {result.config.plan.map((p) => (
              <TimelineItem key={p.step}>
                <TimelineConnector>
                  <CircleArrowDownIcon />
                </TimelineConnector>
                {p.step === "extraction" && (
                  <TimelineContent>
                    <TimelineTitle fontWeight={"bold"}>抽出 ({result.config.extraction.model})</TimelineTitle>
                    <TimelineDescription>
                      コメントデータから意見を抽出するステップです。
                      <br />
                    </TimelineDescription>
                    <HStack>
                      <Button
                        variant={"outline"}
                        size={"xs"}
                        onClick={() =>
                          setSelectedData({
                            title: `抽出 - ${p.step}`,
                            body: result.config.extraction.source_code,
                          })
                        }
                      >
                        ソースコード
                      </Button>
                      <Button
                        variant={"outline"}
                        size={"xs"}
                        onClick={() =>
                          setSelectedData({
                            title: `抽出 - ${p.step}`,
                            body: result.config.extraction.prompt,
                          })
                        }
                      >
                        プロンプト
                      </Button>
                    </HStack>
                  </TimelineContent>
                )}
                {p.step === "embedding" && (
                  <TimelineContent>
                    <TimelineTitle fontWeight={"bold"}>
                      埋め込み (
                      {result.config.is_embedded_at_local
                        ? "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"
                        : result.config.embedding.model}
                      )
                    </TimelineTitle>
                    <TimelineDescription>
                      抽出された意見に対して埋め込み（ベクトル表現）を生成するステップです。
                      <br />
                      これにより、意見の内容を数値ベクトルとして表現します。
                    </TimelineDescription>
                    <HStack>
                      <Button
                        variant={"outline"}
                        size={"xs"}
                        onClick={() =>
                          setSelectedData({
                            title: `埋め込み - ${p.step}`,
                            body: result.config.embedding.source_code,
                          })
                        }
                      >
                        ソースコード
                      </Button>
                    </HStack>
                  </TimelineContent>
                )}
                {p.step === "hierarchical_clustering" && (
                  <TimelineContent>
                    <TimelineTitle fontWeight={"bold"}>意見グループ化</TimelineTitle>
                    <TimelineDescription>
                      埋め込みベクトルの値に基づいて意見の意見グループ化を行うステップです。
                      <br />
                    </TimelineDescription>
                    <HStack>
                      <Button
                        variant={"outline"}
                        size={"xs"}
                        onClick={() =>
                          setSelectedData({
                            title: `意見グループ化 - ${p.step}`,
                            body: result.config.hierarchical_clustering.source_code,
                          })
                        }
                      >
                        ソースコード
                      </Button>
                    </HStack>
                  </TimelineContent>
                )}
                {p.step === "hierarchical_initial_labelling" && (
                  <TimelineContent>
                    <TimelineTitle fontWeight={"bold"}>
                      初期ラベリング ({result.config.hierarchical_initial_labelling.model})
                    </TimelineTitle>
                    <TimelineDescription>
                      意見グループ化の結果に対して、各意見グループに適切なタイトル・説明文を生成（ラベリング）するステップです。
                      <br />
                      このステップでは、最も細かい粒度の意見グループ（最下層の意見グループ）に対して、各意見グループに属する意見に基づいて意見グループのタイトルと説明文を生成します。
                    </TimelineDescription>
                    <HStack>
                      <Button
                        variant={"outline"}
                        size={"xs"}
                        onClick={() =>
                          setSelectedData({
                            title: `初期ラベリング - ${p.step}`,
                            body: result.config.hierarchical_initial_labelling.source_code,
                          })
                        }
                      >
                        ソースコード
                      </Button>
                      <Button
                        variant={"outline"}
                        size={"xs"}
                        onClick={() =>
                          setSelectedData({
                            title: `初期ラベリング - ${p.step}`,
                            body: result.config.hierarchical_initial_labelling.prompt,
                          })
                        }
                      >
                        プロンプト
                      </Button>
                    </HStack>
                  </TimelineContent>
                )}
                {p.step === "hierarchical_merge_labelling" && (
                  <TimelineContent>
                    <TimelineTitle fontWeight={"bold"}>
                      統合ラベリング ({result.config.hierarchical_merge_labelling.model})
                    </TimelineTitle>
                    <TimelineDescription>
                      意見グループを統合し、統合されたグループのタイトルと説明文を生成（ラベリング）するステップです。
                      <br />
                      このステップでは、下層の意見グループのタイトル及び説明文と、意見に基づいて上層の意見グループのタイトル及び説明文を生成します。
                    </TimelineDescription>
                    <HStack>
                      <Button
                        variant={"outline"}
                        size={"xs"}
                        onClick={() =>
                          setSelectedData({
                            title: `統合ラベリング - ${p.step}`,
                            body: result.config.hierarchical_merge_labelling.source_code,
                          })
                        }
                      >
                        ソースコード
                      </Button>
                      <Button
                        variant={"outline"}
                        size={"xs"}
                        onClick={() =>
                          setSelectedData({
                            title: `統合ラベリング - ${p.step}`,
                            body: result.config.hierarchical_merge_labelling.prompt,
                          })
                        }
                      >
                        プロンプト
                      </Button>
                    </HStack>
                  </TimelineContent>
                )}
                {p.step === "hierarchical_overview" && (
                  <TimelineContent>
                    <TimelineTitle fontWeight={"bold"}>
                      要約 ({result.config.hierarchical_overview.model})
                    </TimelineTitle>
                    <TimelineDescription>
                      意見グループの概要を作成するステップです。
                      <br />
                      各意見グループのタイトル及び説明文をもとに、全体の概要をまとめます。
                    </TimelineDescription>
                    <HStack>
                      <Button
                        variant={"outline"}
                        size={"xs"}
                        onClick={() =>
                          setSelectedData({
                            title: `要約 - ${p.step}`,
                            body: result.config.hierarchical_overview.source_code,
                          })
                        }
                      >
                        ソースコード
                      </Button>
                      <Button
                        variant={"outline"}
                        size={"xs"}
                        onClick={() =>
                          setSelectedData({
                            title: `要約 - ${p.step}`,
                            body: result.config.hierarchical_overview.prompt,
                          })
                        }
                      >
                        プロンプト
                      </Button>
                    </HStack>
                  </TimelineContent>
                )}
                {p.step === "hierarchical_aggregation" && (
                  <TimelineContent>
                    <TimelineTitle fontWeight={"bold"}>出力</TimelineTitle>
                    <TimelineDescription>
                      最終的な結果を出力するステップです。
                      <br />
                      意見および各分析結果を含むJSONファイルを出力します。
                    </TimelineDescription>
                    <HStack>
                      <Button
                        variant={"outline"}
                        size={"xs"}
                        onClick={() =>
                          setSelectedData({
                            title: `出力 - ${p.step}`,
                            body: result.config.hierarchical_aggregation.source_code,
                          })
                        }
                      >
                        ソースコード
                      </Button>
                    </HStack>
                  </TimelineContent>
                )}
                {p.step === "hierarchical_visualization" && (
                  <TimelineContent>
                    <TimelineTitle fontWeight={"bold"}>表示</TimelineTitle>
                    <TimelineDescription>
                      出力されたJSONファイルをグラフィカルに表示するステップです。
                      <br />
                      意見グループの概要、意見の内容などを可視化します。あなたが見ているこの画面が出来上がります。
                    </TimelineDescription>
                    <HStack>
                      <Button
                        variant={"outline"}
                        size={"xs"}
                        onClick={() =>
                          setSelectedData({
                            title: `表示 - ${p.step}`,
                            body: result.config.hierarchical_visualization.source_code,
                          })
                        }
                      >
                        ソースコード
                      </Button>
                    </HStack>
                  </TimelineContent>
                )}
              </TimelineItem>
            ))}
          </TimelineRoot>
        </Presence>
      </Box>

      <DrawerRoot open={!!selectedData} size={"xl"} onOpenChange={() => setSelectedData(null)}>
        <DrawerBackdrop />
        <DrawerContent>
          <DrawerHeader>
            <DrawerTitle>{selectedData?.title}</DrawerTitle>
          </DrawerHeader>
          <DrawerBody fontSize={"xs"}>
            <Box p={5} borderRadius={5} bgColor={"#111"} color={"#fff"} whiteSpace={"pre-wrap"} className={"code"}>
              {selectedData?.body}
            </Box>
          </DrawerBody>
          <DrawerFooter>
            <Button w={"150px"} onClick={() => setSelectedData(null)}>
              閉じる
            </Button>
          </DrawerFooter>
        </DrawerContent>
      </DrawerRoot>
    </Box>
  );
}
