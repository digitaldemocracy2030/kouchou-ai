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
import { useMessages } from "@/lib/i18n/LanguageContext";
import type { Config, Result } from "@/type";
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
import { Fragment, useState } from "react";
import { chatModelDisplayName, embeddingModelDisplayName } from "./modelDisplay";

type ReportProps = {
  result: Result;
};

type StepDetail = {
  model?: string;
  sourceCode: string;
  prompt?: string;
};

/** 分析手順の各ステップで表示するモデル名・ソースコード・プロンプトを設定から取り出す。 */
function getStepDetail(step: string, config: Config, azureLabel: string): StepDetail | undefined {
  switch (step) {
    case "extraction":
      return {
        model: chatModelDisplayName(config, config.extraction.model, azureLabel),
        sourceCode: config.extraction.source_code,
        prompt: config.extraction.prompt,
      };
    case "embedding":
      return {
        model: embeddingModelDisplayName(config, azureLabel),
        sourceCode: config.embedding.source_code,
      };
    case "hierarchical_clustering":
      return { sourceCode: config.hierarchical_clustering.source_code };
    case "hierarchical_initial_labelling":
      return {
        model: chatModelDisplayName(config, config.hierarchical_initial_labelling.model, azureLabel),
        sourceCode: config.hierarchical_initial_labelling.source_code,
        prompt: config.hierarchical_initial_labelling.prompt,
      };
    case "hierarchical_merge_labelling":
      return {
        model: chatModelDisplayName(config, config.hierarchical_merge_labelling.model, azureLabel),
        sourceCode: config.hierarchical_merge_labelling.source_code,
        prompt: config.hierarchical_merge_labelling.prompt,
      };
    case "hierarchical_overview":
      return {
        model: chatModelDisplayName(config, config.hierarchical_overview.model, azureLabel),
        sourceCode: config.hierarchical_overview.source_code,
        prompt: config.hierarchical_overview.prompt,
      };
    case "hierarchical_aggregation":
      return { sourceCode: config.hierarchical_aggregation.source_code };
    case "hierarchical_visualization":
      return { sourceCode: config.hierarchical_visualization.source_code };
    default:
      return undefined;
  }
}

export function Analysis({ result }: ReportProps) {
  const messages = useMessages();
  const [selectedData, setSelectedData] = useState<{
    title: string;
    body: string;
  } | null>(null);
  const clusterNum = getClusterNum(result);
  const level1ClusterNum = clusterNum[1] ?? 0;
  const level2ClusterNum = clusterNum[2];
  const { open, onToggle } = useDisclosure();

  return (
    <Box mx={"auto"} maxW={"750px"} mb={12} cursor={"default"}>
      <Separator mt={20} mb={12} />
      <Heading textAlign={"center"} fontSize={"xl"} mb={5}>
        {messages.analysisOverview}
      </Heading>
      <HStack mb={5} justify={"center"}>
        <Tooltip content={messages.commentCountTooltip} openDelay={0} closeDelay={0}>
          <VStack gap={0} w={"200px"}>
            <Icon mb={2}>
              <MessageCircleWarningIcon size={"30px"} />
            </Icon>
            <Text className={"headingColor"} fontSize={"3xl"} fontWeight={"bold"} lineHeight={1} mb={1}>
              {result.comment_num.toLocaleString()}
            </Text>
            <Text fontSize={"xs"}>{messages.commentCount}</Text>
          </VStack>
        </Tooltip>
        <ChevronRightIcon />
        <Tooltip content={messages.opinionCountTooltip} openDelay={0} closeDelay={0}>
          <VStack gap={0} w={"200px"}>
            <Icon mb={2}>
              <MessagesSquareIcon size={"30px"} />
            </Icon>
            <Text className={"headingColor"} fontSize={"3xl"} fontWeight={"bold"} lineHeight={1} mb={1}>
              {result.arguments.length.toLocaleString()}
            </Text>
            <Text fontSize={"xs"}>{messages.extractedOpinionCount}</Text>
          </VStack>
        </Tooltip>
        <ChevronRightIcon />
        <Tooltip content={messages.clusterCountTooltip} openDelay={0} closeDelay={0}>
          <VStack gap={0} w={"200px"}>
            <Icon mb={2}>
              <ClipboardCheckIcon size={"30px"} />
            </Icon>
            <HStack gap={1} alignItems={"center"}>
              <Text className={"headingColor"} fontSize={"3xl"} fontWeight={"bold"} lineHeight={1} mb={1}>
                {level1ClusterNum.toLocaleString()}
              </Text>
              {level2ClusterNum !== undefined ? (
                <>
                  <Text fontSize={"md"}>→</Text>
                  <Text className={"headingColor"} fontSize={"3xl"} fontWeight={"bold"} lineHeight={1} mb={1}>
                    {level2ClusterNum.toLocaleString()}
                  </Text>
                </>
              ) : null}
            </HStack>
            <Text fontSize={"xs"}>{messages.clusterCount}</Text>
          </VStack>
        </Tooltip>
      </HStack>
      <Text mb={5}>{result.config.intro}</Text>
      <Box>
        <Flex align={"center"} mb={5}>
          <Heading fontSize={"md"}>{messages.analysisSteps}</Heading>
          <Button variant={"outline"} size={"sm"} ml={2} onClick={onToggle}>
            {open ? messages.hide : messages.show}
          </Button>
        </Flex>
        <Presence present={open}>
          <TimelineRoot size={"lg"}>
            {result.config.plan.map((p) => {
              const text = messages.steps[p.step];
              const detail = getStepDetail(p.step, result.config, messages.azureServerModel);
              const title = text ? `${text.title}${detail?.model ? ` (${detail.model})` : ""}` : p.step;
              return (
                <TimelineItem key={p.step}>
                  <TimelineConnector>
                    <CircleArrowDownIcon />
                  </TimelineConnector>
                  {text && detail && (
                    <TimelineContent>
                      <TimelineTitle fontWeight={"bold"}>{title}</TimelineTitle>
                      <TimelineDescription>
                        {text.description.map((line, index) => (
                          <Fragment key={line}>
                            {line}
                            {index < text.description.length - 1 && <br />}
                          </Fragment>
                        ))}
                        <br />
                      </TimelineDescription>
                      <HStack>
                        <Button
                          variant={"outline"}
                          size={"xs"}
                          onClick={() =>
                            setSelectedData({
                              title: `${text.title} - ${p.step}`,
                              body: detail.sourceCode,
                            })
                          }
                        >
                          {messages.sourceCode}
                        </Button>
                        {detail.prompt !== undefined && (
                          <Button
                            variant={"outline"}
                            size={"xs"}
                            onClick={() =>
                              setSelectedData({
                                title: `${text.title} - ${p.step}`,
                                body: detail.prompt ?? "",
                              })
                            }
                          >
                            {messages.prompt}
                          </Button>
                        )}
                      </HStack>
                    </TimelineContent>
                  )}
                </TimelineItem>
              );
            })}
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
              {messages.close}
            </Button>
          </DrawerFooter>
        </DrawerContent>
      </DrawerRoot>
    </Box>
  );
}
