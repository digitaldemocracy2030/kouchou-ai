"use client";

import { getImageFromServerSrc } from "@/app/utils/image-src";
import { BroadlisteningGuide } from "@/components/report/BroadlisteningGuide";
import type { Meta } from "@/type";
import { HStack, Image } from "@chakra-ui/react";
import { useEffect, useState } from "react";

type Props = {
  meta: Meta | null;
};

export function Header({ meta }: Props) {
  // reporter.png（作成者画像）が存在するかどうかを管理
  // 204(No Content)の場合は画像を表示しない
  const [hasImage, setHasImage] = useState(false);

  // reporter.pngの存在確認
  // 画像が存在する場合のみ画像を表示する（リンク切れやキャッシュ問題を防ぐため）
  useEffect(() => {
    if (!meta) {
      setHasImage(false);
      return;
    }
    fetch(getImageFromServerSrc("/meta/reporter.png"))
      .then(res => setHasImage(res.status === 200))
      .catch(() => setHasImage(false));
  }, [meta]);

  return (
    <HStack justify="space-between" mb={8} mx={"auto"} maxW={"1200px"}>
      <HStack>
        {meta && hasImage && (
          <Image
            src={getImageFromServerSrc("/meta/reporter.png")}
            mx={"auto"}
            objectFit={"cover"}
            maxH={{ base: "40px", md: "60px" }}
            maxW={{ base: "120px", md: "200px" }}
            alt={meta.reporter}
          />
        )}
      </HStack>
      <BroadlisteningGuide />
    </HStack>
  );
}
