"use client";

import { Button } from "@/components/ui/button";
import type { Report } from "@/type";
import { Box, Flex, HStack, Heading, Icon, Text, VStack } from "@chakra-ui/react";
import { Eye, EyeClosedIcon, LockKeyhole, Plus } from "lucide-react";
import { useState } from "react";
import { BuildDownloadButton } from "./BuildDownloadButton/BuildDownloadButton";
import { Empty } from "./Empty";
import { ReportCardList } from "./ReportCardList";

type Props = {
  reports: Report[];
};

export function PageContent({ reports: _reports }: Props) {
  const [reports, setReports] = useState<Report[]>(_reports);

  const publicCount = reports.filter((report) => report.visibility === "public").length;
  const unlistedCount = reports.filter((report) => report.visibility === "unlisted").length;
  const privateCount = reports.filter((report) => report.visibility === "private").length;

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
                {publicCount}
              </Text>
            </VStack>
            <VStack gap="2" w="88px" h="80px" bg="white" justifyContent="center">
              <Icon color="font.limitedPublic">
                <LockKeyhole />
              </Icon>
              <Text textStyle="body/lg/bold" lineHeight="1.38">
                {unlistedCount}
              </Text>
            </VStack>
            <VStack gap="2" w="88px" h="80px" bg="white" justifyContent="center">
              <Icon color="font.error">
                <EyeClosedIcon />
              </Icon>
              <Text textStyle="body/lg/bold" lineHeight="1.38">
                {privateCount}
              </Text>
            </VStack>
          </Flex>
        </Flex>
      </Box>
      <Flex justifyContent="flex-end" mb="4">
        <Button size="md" asChild>
          <a href="/create">
            <Plus />
            新規作成
          </a>
        </Button>
      </Flex>
      {reports.length === 0 ? (
        <Empty />
      ) : (
        <>
          <ReportCardList reports={reports} setReports={setReports} />
          <HStack justify="center" mt={10}>
            <BuildDownloadButton />
          </HStack>
        </>
      )}
    </>
  );
}
