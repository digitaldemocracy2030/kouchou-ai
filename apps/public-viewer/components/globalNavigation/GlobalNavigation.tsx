import { Box } from "@chakra-ui/react";
import { CircleHelp, Files } from "lucide-react";
import { MdNavigation } from "./md/MdNavigation";
import { SmNavigation } from "./sm/SmNavigation";

const navItems = [
  { href: "/", label: "レポート一覧", icon: <Files /> },
  { href: "/faq", label: "よくあるご質問", icon: <CircleHelp /> },
] as const;

export type NavItems = typeof navItems;

export function GlobalNavigation() {
  return (
    <>
      <Box hideFrom="md" py="2">
        <SmNavigation navItems={navItems} />
      </Box>
      <Box hideBelow="md">
        <MdNavigation navItems={navItems} />
      </Box>
    </>
  );
}
