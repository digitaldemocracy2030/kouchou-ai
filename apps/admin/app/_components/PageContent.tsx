"use client";

import { Button } from "@/components/ui/button";
import type { Report } from "@/type";
import { Box, Flex, HStack, Heading, Icon, Text, VStack } from "@chakra-ui/react";
import { Eye, EyeClosedIcon, LockKeyhole, Plus } from "lucide-react";
import Link from "next/link";
import { useMemo } from "react";
import { BuildDownloadButton } from "./BuildDownloadButton/BuildDownloadButton";
import { ReportCardList } from "./ReportCardList";

type Props = {
  reports: Report[];
};

export function PageContent({ reports }: Props) {
  const counts = useMemo(
    () => ({
      public: reports.filter((report) => report.visibility === "public").length,
      unlisted: reports.filter((report) => report.visibility === "unlisted").length,
      private: reports.filter((report) => report.visibility === "private").length,
    }),
    [reports],
  );

  return (
    <>
      <Box mb="12">
        <Flex justifyContent="space-between">
          <Heading textStyle="heading/xl">レポート管理</Heading>
          <Flex gap="3">
            <VStack gap="2" w="88px" h="80px" bg="white" justifyContent="center">
              <Icon color="font.public">
                <Eye />
              </Icon>
              <Text textStyle="body/lg/bold" lineHeight="1.38">
                {counts.public}
              </Text>
            </VStack>
            <VStack gap="2" w="88px" h="80px" bg="white" justifyContent="center">
              <Icon color="font.limitedPublic">
                <LockKeyhole />
              </Icon>
              <Text textStyle="body/lg/bold" lineHeight="1.38">
                {counts.unlisted}
              </Text>
            </VStack>
            <VStack gap="2" w="88px" h="80px" bg="white" justifyContent="center">
              <Icon color="font.error">
                <EyeClosedIcon />
              </Icon>
              <Text textStyle="body/lg/bold" lineHeight="1.38">
                {counts.private}
              </Text>
            </VStack>
          </Flex>
        </Flex>
      </Box>
      {reports.length > 0 && (
        <Flex justifyContent="flex-end" mb="4">
          <Button size="md" asChild>
            <Link href="/create">
              <Plus />
              新規作成
            </Link>
          </Button>
        </Flex>
      )}
      <ReportCardList reports={reports} />
      {reports.length > 0 && (
        <HStack justify="center" mt={10}>
          <BuildDownloadButton />
        </HStack>
      )}
    </>
  );
}
