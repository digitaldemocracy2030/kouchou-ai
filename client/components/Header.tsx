"use client";

import { getImageFromServerSrc } from "@/app/utils/image-src";
import { BroadlisteningGuide } from "@/components/report/BroadlisteningGuide";
import type { Meta } from "@/type";
import { HStack, Image } from "@chakra-ui/react";
import { useState } from "react";

type Props = {
  meta: Meta | null;
};

export function Header({ meta }: Props) {
  const [imageLoaded, setImageLoaded] = useState(false);

  return (
    <HStack justify="space-between" mb={8} mx={"auto"} maxW={"1200px"}>
      <HStack>
        {meta && !meta.isDefault && (
          <Image
            src={getImageFromServerSrc("/meta/reporter.png")}
            mx={"auto"}
            objectFit={"cover"}
            maxH={{ base: "40px", md: "60px" }}
            maxW={{ base: "120px", md: "200px" }}
            alt={meta.reporter}
            onLoad={() => setImageLoaded(true)}
            display={imageLoaded ? "block" : "none"}
          />
        )}
      </HStack>
      <BroadlisteningGuide />
    </HStack>
  );
}
