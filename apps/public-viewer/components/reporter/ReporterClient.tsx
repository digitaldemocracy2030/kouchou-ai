"use client";

/**
 * Reporter のクライアント版。
 *
 * 既存の `Reporter` は async サーバコンポーネント（reporter.png の存在を await で確認する）
 * のため、standalone のクライアントツリー内で描画すると React #482 (async Client Component)
 * で落ちる。standalone は API と同一オリジンなので、画像の存在確認も表示も実行時に
 * クライアントで行い、内側の `ReporterContent`（"use client"）をそのまま使う。
 */

import type { Meta } from "@/type";
import { Image } from "@chakra-ui/react";
import { useEffect, useState } from "react";
import { ReporterContent } from "./ReporterContent";

const IMAGE_PATH = "/meta/reporter.png";

export function ReporterClient({ meta, apiBase = "" }: { meta: Meta; apiBase?: string }) {
  const [hasImage, setHasImage] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetch(`${apiBase}${IMAGE_PATH}`)
      .then((res) => {
        if (!cancelled) setHasImage(res.status === 200);
      })
      .catch(() => {
        if (!cancelled) setHasImage(false);
      });
    return () => {
      cancelled = true;
    };
  }, [apiBase]);

  return (
    <ReporterContent meta={meta}>
      {hasImage ? <Image src={`${apiBase}${IMAGE_PATH}`} alt={meta.reporter} maxW="150px" /> : null}
    </ReporterContent>
  );
}
