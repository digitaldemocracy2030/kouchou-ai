import { Button } from "@/components/ui/button";
import { Box, Image, Link, Text, VStack } from "@chakra-ui/react";
import { Plus } from "lucide-react";

export function Empty() {
  return (
    <VStack mt="8" gap="0" textAlign="center">
      <Text textStyle="body/lg/bold">レポートが0件です</Text>
      <Text textStyle="body/md" mt={5}>
        レポートが作成されるとここに一覧が表示され、
        <Box as="br" display={{ base: "none", md: "block" }} />
        公開やダウンロードなどの操作が行えるようになります。
      </Text>
      <Button size="xl" mt="4" asChild>
        <Link href="/create">
          <Plus />
          新規作成
        </Link>
      </Button>
      <Image src="images/report-empty.png" mt="4" />
    </VStack>
  );
}
