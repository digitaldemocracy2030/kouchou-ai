import { HStack } from "@chakra-ui/react";
import type { NavItems } from "../GlobalNavigation";
import { NavItem } from "./NavItem";

type Props = {
  navItems: NavItems;
};

export function MdNavigation({ navItems }: Props) {
  return (
    <HStack gap="1" hideBelow="md">
      {navItems.map((item) => (
        <NavItem key={item.href} {...item} />
      ))}
    </HStack>
  );
}
