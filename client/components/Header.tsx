"use client";

import { BroadlisteningGuide } from "@/components/report/BroadlisteningGuide";
import { HStack, Image, useBreakpointValue } from "@chakra-ui/react";

export function Header() {
  const logoSrc = useBreakpointValue({
    base: "/images/logo-sp.svg",
    md: "/images/logo.svg",
  });

  return (
    <HStack justify="space-between" py="5" mb={8} mx={"auto"} maxW={"1200px"}>
      <Image src={logoSrc} alt="広聴AI" />
      <BroadlisteningGuide />
    </HStack>
  );
}
