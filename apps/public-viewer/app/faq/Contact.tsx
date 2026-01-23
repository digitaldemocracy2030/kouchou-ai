import { Button } from "@/components/ui/button";
import { Box, Flex, Heading, Image, Text, VStack } from "@chakra-ui/react";
import { ArrowUpRight } from "lucide-react";

export function Contact() {
  return (
    <>
      <Heading textStyle="heading/2xl" pt="12" pb="6">
        お問い合わせ
      </Heading>
      <Box
        padding="4px"
        bg="linear-gradient(241.3deg, #FDC7FD 17.69%, #ACFBFF 50.31%, #D9E0FF 82.31%)"
        borderRadius="2xl"
      >
        <Box bg="white" borderRadius="12px" p={{ base: "6", md: "8" }}>
          <Flex gap="8" flexDirection={{ base: "column-reverse", lg: "row" }} alignItems="center">
            <Image maxW={{ base: "auto", md: "440px" }} src="/images/contact-hello.webp" alt="" />
            <VStack alignItems={{ base: "center", lg: "flex-start" }} gap="4">
              <Text textStyle="body/md">
                このページで解決できなかった内容や、その他のご質問がございましたら、
                デジタル民主主義2030のslackコミュニティのチャンネル「#6_ホストユーザー相談」でお気軽にお声がけください。チーム一同、迅速にサポートいたします。
              </Text>
              <Button variant="secondary" size="md" asChild>
                <a href="https://dd2030.slack.com" target="_blank" rel="noopener noreferrer">
                  <Box hideFrom="md">コミュニティで質問する</Box>
                  <Box hideBelow="md">slackコミュニティで質問する</Box>
                  <ArrowUpRight />
                </a>
              </Button>
            </VStack>
          </Flex>
        </Box>
      </Box>
    </>
  );
}
