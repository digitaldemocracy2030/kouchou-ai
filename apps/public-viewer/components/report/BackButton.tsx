"use client";

import Link from "next/link";

import { useMessages } from "@/lib/i18n/LanguageContext";
import { Box, Button } from "@chakra-ui/react";
import { ChevronLeft } from "lucide-react";

export function BackButton() {
  const messages = useMessages();
  return (
    <Box w={"fit-content"} mx={"auto"}>
      <Link href={"/"}>
        <Button variant={"outline"} size={"md"}>
          <ChevronLeft />
          {messages.backToList}
        </Button>
      </Link>
    </Box>
  );
}
