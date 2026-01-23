import Link from "next/link";

import { Box, Button } from "@chakra-ui/react";
import { ChevronLeft } from "lucide-react";

export function BackButton() {
  return (
    <Box w={"fit-content"} mx={"auto"}>
      <Link href={"/"}>
        <Button variant={"outline"} size={"md"}>
          <ChevronLeft />
          一覧へ戻る
        </Button>
      </Link>
    </Box>
  );
}
