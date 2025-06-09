"use client";

import { BroadlisteningGuide } from "@/components/report/BroadlisteningGuide";
import { HStack, Image } from "@chakra-ui/react";

export function Header() {
  return (
    <HStack justify="space-between" py="5" mb={8} mx={"auto"} maxW={"1200px"}>
      <Image src="/images/dd2030-logo.svg" alt="デジタル民主主義2030" w="180px" h="60px" />
      <BroadlisteningGuide />
    </HStack>
  );
}
