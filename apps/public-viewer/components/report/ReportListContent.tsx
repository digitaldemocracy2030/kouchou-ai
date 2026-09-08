import { getRelativeUrl } from "@/app/utils/image-src";
import type { Meta, Report } from "@/type";
import { Box, Card, HStack, Image, Text, VStack } from "@chakra-ui/react";
import Link from "next/link";

export function ReportListContent({ reports, meta }: { reports: Report[]; meta: Meta }) {
  return (
    <>
      {reports.length === 0 ? (
        <EmptyState />
      ) : (
        reports.map((report) => (
          <Link key={report.slug} href={`/${report.slug}`}>
            <Card.Root
              size="md"
              key={report.slug}
              mb={4}
              borderLeftWidth={10}
              borderLeftColor={meta.brandColor || "#2577b1"}
              cursor={"pointer"}
              className={"shadow"}
            >
              <Card.Body>
                <HStack>
                  <Box>
                    <Card.Title>
                      <Text fontSize={"lg"} color={"#2577b1"} mb={1} lineClamp="2">
                        {report.title}
                      </Text>
                    </Card.Title>
                    {report.createdAt && (
                      <Text fontSize={"xs"} color={"gray.500"} mb={1}>
                        作成日時: {new Date(report.createdAt).toLocaleString("ja-JP", { timeZone: "Asia/Tokyo" })}
                      </Text>
                    )}
                    <Card.Description lineClamp={{ base: 3, md: 2 }}>{report.description || ""}</Card.Description>
                  </Box>
                </HStack>
              </Card.Body>
            </Card.Root>
          </Link>
        ))
      )}
    </>
  );
}

const EmptyState = () => {
  return (
    <VStack mt={8} mb={12} gap={0} lineHeight={2}>
      <Text fontSize="18px" fontWeight="bold">
        レポートが0件です
      </Text>
      <Text fontSize="14px" textAlign={{ md: "center" }} mt={5}>
        レポート作成が完了し公開されると、ここに一覧が表示されます。
        <Box as="br" display={{ base: "none", md: "block" }} />
        レポートが公開されるまでしばらくお待ちください。
      </Text>
      <Image src={getRelativeUrl("/images/report-empty.png")} mt={8} />
    </VStack>
  );
};
