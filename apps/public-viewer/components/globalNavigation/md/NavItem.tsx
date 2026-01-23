"use client";

import { Box, Link, Text, VStack } from "@chakra-ui/react";
import NextLink from "next/link";
import { usePathname } from "next/navigation";

type Props = {
  href: string;
  label: string;
  icon: React.ReactNode;
};

export function NavItem({ href, label, icon }: Props) {
  const pathname = usePathname();
  const normalize = (p: string) => p.replace(/\/+$/, "");
  const isActive = normalize(pathname ?? "") === normalize(href);

  return (
    <Box
      p="3"
      borderBottom={isActive ? "2px solid" : "none"}
      h="auto"
      borderRadius="none"
      _hover={{
        color: !isActive ? "font.link" : "currentcolor",
      }}
    >
      <Link asChild aria-current={isActive ? "page" : undefined}>
        <NextLink href={href}>
          <VStack>
            {icon}
            <Text textStyle="body/sm">{label}</Text>
          </VStack>
        </NextLink>
      </Link>
    </Box>
  );
}
