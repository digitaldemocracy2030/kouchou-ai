"use server";

import { getImageFromServerSrc } from "@/app/utils/image-src";
import type { Meta } from "@/type";
import { Image } from "@chakra-ui/react";
import { ReporterContent } from "./ReporterContent";

async function ReporterImage({
  reporterName,
}: {
  reporterName: string;
}) {
  const src: string = getImageFromServerSrc("/meta/reporter.png");
  try {
    const res = await fetch(src, {
      method: "GET",
    });

    if (res.status === 200) {
      return <Image src={src} alt={reporterName} maxW="150px" />;
    }
  } catch (error) {
    console.error("Failed to fetch reporter image:", error);
  }

  return null;
}

export async function Reporter({ meta }: { meta: Meta }) {
  return (
    <ReporterContent meta={meta}>
      <ReporterImage reporterName={meta.reporter || ""} />
    </ReporterContent>
  );
}
