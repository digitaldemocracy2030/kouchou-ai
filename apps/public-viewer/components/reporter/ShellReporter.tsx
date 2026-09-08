"use client";

import { getImageFromServerSrc } from "@/app/utils/image-src";
import type { Meta } from "@/type";
import { Image } from "@chakra-ui/react";
import { useState } from "react";
import { ReporterContent } from "./ReporterContent";

const imagePath = "/meta/reporter.png";

/**
 * shell ビルド用のレポーター表示。
 *
 * `Reporter` はサーバー側で画像の有無を確認する server component なので
 * shell では使えない。同梱アセットの有無は読み込み結果で判定する。
 */
export function ShellReporter({ meta }: { meta: Meta }) {
  const [hasImage, setHasImage] = useState(true);

  return (
    <ReporterContent meta={meta}>
      {hasImage ? (
        <Image
          src={getImageFromServerSrc(imagePath)}
          alt={meta.reporter}
          maxW="150px"
          onError={() => setHasImage(false)}
        />
      ) : null}
    </ReporterContent>
  );
}
