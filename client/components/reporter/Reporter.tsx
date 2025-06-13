import type { Meta } from "@/type";
import { Image } from "@chakra-ui/react";
import { ReporterContent } from "./ReporterContent";

const imagePath = "/meta/reporter.png";

function reporterImageSrc() {
  // ビルド方法に応じて、clientから取得できる画像のパスを返す
  if (process.env.NEXT_PUBLIC_OUTPUT_MODE === "export") {
    return imagePath;
  }
  return new URL(imagePath, process.env.NEXT_PUBLIC_API_BASEPATH).toString();
}

async function hasReporterImage() {
  const url = new URL(imagePath, process.env.API_BASEPATH).toString();
  try {
    const res = await fetch(url);
    return res.status === 200;
  } catch {
    return false;
  }
}

async function ReporterImage({
  reporterName,
}: {
  reporterName: string;
}) {
  if (await hasReporterImage()) {
    return <Image src={reporterImageSrc()} alt={reporterName} maxW="150px" />;
  }
  return null;
}

export async function Reporter({ meta }: { meta: Meta }) {
  return (
    <ReporterContent meta={meta}>
      <ReporterImage reporterName={meta.reporter} />
    </ReporterContent>
  );
}
