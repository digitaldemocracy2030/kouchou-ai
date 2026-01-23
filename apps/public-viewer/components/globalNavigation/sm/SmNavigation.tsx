import { CloseButton } from "@/components/ui/close-button";
import { DrawerBody, Flex, Icon, Link, Portal, Text, VStack } from "@chakra-ui/react";
import { Menu, X } from "lucide-react";
import NextLink from "next/link";
import {
  DrawerBackdrop,
  DrawerCloseTrigger,
  DrawerContent,
  DrawerHeader,
  DrawerPositioner,
  DrawerRoot,
  DrawerTrigger,
} from "../../ui/drawer";
import { IconButton } from "../../ui/icon-button";
import type { NavItems } from "../GlobalNavigation";

type Props = {
  navItems: NavItems;
};

export function SmNavigation({ navItems }: Props) {
  return (
    <DrawerRoot>
      <DrawerTrigger asChild>
        <IconButton variant="ghost" size="xl" hideFrom="md" aria-label="メニューを開く">
          <Menu size="32px" />
        </IconButton>
      </DrawerTrigger>
      <Portal>
        <DrawerBackdrop />
        <DrawerPositioner>
          <DrawerContent>
            <DrawerHeader />
            <DrawerBody>
              <VStack alignItems="start" gap="6">
                {navItems.map((item) => (
                  <Link key={item.href} asChild>
                    <NextLink href={item.href}>
                      <Flex gap="3" alignItems="center">
                        <Icon color="font.link" w="8" h="8">
                          {item.icon}
                        </Icon>
                        <Text textStyle="body/md/bold">{item.label}</Text>
                      </Flex>
                    </NextLink>
                  </Link>
                ))}
              </VStack>
            </DrawerBody>
            <DrawerCloseTrigger asChild>
              <CloseButton>
                <Icon as={X} w="8" h="8" color="font.link" />
              </CloseButton>
            </DrawerCloseTrigger>
          </DrawerContent>
        </DrawerPositioner>
      </Portal>
    </DrawerRoot>
  );
}
