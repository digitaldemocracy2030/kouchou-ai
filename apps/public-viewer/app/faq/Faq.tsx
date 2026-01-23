"use client";

import { Accordion, Box, Center, HStack, Heading, Text } from "@chakra-ui/react";
import { Minus, Plus } from "lucide-react";

const faqs = [
  {
    title: "広聴AIについて",
    items: [
      {
        question: "広聴AIとは？",
        answer:
          "多くの意見を効率的に分析・可視化するブロードリスニングツールです。ファイルをアップロードするだけでAIが自動的に意見を抽出・グループ化して可視化し、今まで手作業で時間がかかっていた整理作業を効率化します。",
      },
      {
        question: "ブロードリスニングとは？",
        answer:
          "大量で多様な意見を収集・分析する手法のことです。AI技術により効率的に整理して理解することで、従来の方法よりも多くの意見を効率的に分析し、有益なインサイトの発見や意思決定のスピードや質の改善を目指しています。",
      },
    ],
  },
  {
    title: "レポートについて",
    items: [
      {
        question: "意見とは？",
        answer:
          "アップロードされた大量のコメントデータの中から、有効な分析対象としてAIが取り出した意見のことです。1人のコメントから複数意見が抽出されることもあります。",
      },
      {
        question: "意見グループとは？",
        answer: "近しい内容の意見をAIが自動的にまとめたグループのことです。",
      },
      {
        question: "全体の図の縦軸と横軸が表してるものは？",
        answer:
          "縦軸と横軸には特定の定義はありません。AIが多次元のデータを図として表現するために2次元の平面に圧縮して表示しています。",
      },
      {
        question: "濃い意見とは？",
        answer:
          "広聴AIにおける「濃い意見」とは、似たような内容の意見がたくさん集まっているグループのことです。「濃い意見」表示に切り替えることで、大量の意見の中から「多くの人が同じことを言っている意見」を素早く見つけることができます。",
      },
      {
        question: "階層とは？",
        answer:
          "広聴AIにおける「階層」とは、意見のまとまり方を大きいテーマから細かい話題へと段階的に閲覧できる表示機能のことです。「階層」表示に切り替えることで、意見の全体像を把握しながら、その中の個別の課題も発見できるようになります。",
      },
    ],
  },
  {
    title: "レポート生成について",
    items: [
      {
        question: "プロンプトとは？",
        answer:
          "AIへの指示文のことです。広聴AIでは、レポート生成時にプロンプトを工夫することで、より目的に適した分析や分類ができるようになります。",
      },
      {
        question: "同じデータでレポートを生成しても図の形が変わるのはなぜですか？",
        answer:
          "AIが図を生成するたびに配置が自動調整されるためです。図の形や意見グループの距離など多少の見た目は変わりますが意見同士の関係性は保たれます。地図を回転させても道路の位置関係が同じなように、分析結果や傾向把握には影響しません。",
      },
    ],
  },
] as const;

export function Faq() {
  return (
    <Box mt="8" color="font.primary">
      <Heading textStyle="heading/2xl" mb="12">
        よくあるご質問
      </Heading>
      {faqs.map((faq) => (
        <Box key={faq.title} mt="8">
          <Heading textStyle="heading/xl" mb="6">
            {faq.title}
          </Heading>
          <Box p="4" bg="white" borderRadius="sm">
            <Accordion.Root collapsible multiple>
              {faq.items.map((item) => (
                <Accordion.Item
                  key={item.question}
                  value={item.question}
                  bg="white"
                  py="4"
                  px={{ base: 0, md: 4 }}
                  _last={{
                    borderBottom: "none",
                  }}
                >
                  <Accordion.ItemTrigger gap="4" alignItems="flex-start">
                    <Center fontWeight="bold" fontSize="xl" w="40px" h="40px" bg="#A1A1AA" color="white" flexShrink="0">
                      Q
                    </Center>
                    <Text textStyle="body/lg/bold">{item.question}</Text>
                    <Accordion.ItemContext>
                      {(context) => (
                        <Center ml="auto" h="40px">
                          {context.expanded ? <Minus /> : <Plus />}
                        </Center>
                      )}
                    </Accordion.ItemContext>
                  </Accordion.ItemTrigger>
                  <Accordion.ItemContent>
                    <Accordion.ItemBody>
                      <HStack alignItems="flex-start" gap="4">
                        <Center
                          fontWeight="bold"
                          fontSize="xl"
                          w="40px"
                          h="40px"
                          flexShrink="0"
                          color="#A1A1AA"
                          border="1px solid"
                          borderColor="#0000005C"
                        >
                          A
                        </Center>
                        <Text textStyle="body/md">{item.answer}</Text>
                      </HStack>
                    </Accordion.ItemBody>
                  </Accordion.ItemContent>
                </Accordion.Item>
              ))}
            </Accordion.Root>
          </Box>
        </Box>
      ))}
    </Box>
  );
}
