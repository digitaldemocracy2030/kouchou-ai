"use client";

import { getImageFromServerSrc } from "@/app/utils/image-src";
import { HStack, Image, useBreakpointValue } from "@chakra-ui/react";
import { GlobalNavigation } from "./globalNavigation/GlobalNavigation";

export function Header() {
  const logoSrc = useBreakpointValue({
    base: getImageFromServerSrc("/images/logo-sp.svg"),
    md: getImageFromServerSrc("/images/logo.svg"),
  });
  return (
    <HStack
      className="container"
      py="0"
      px="6"
      justifyContent="space-between"
      alignItems="center"
      bg="white"
      borderBottom="1px solid"
      borderColor="border.weak"
    >
      <Image src={logoSrc} alt="広聴AI" />
      <GlobalNavigation />
    </HStack>
  );
}
