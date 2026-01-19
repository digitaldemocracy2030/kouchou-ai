import { getImageFromServerSrc } from "@/app/utils/image-src";
import type { Meta } from "@/type";
import { Image } from "@chakra-ui/react";
import { ReporterContent } from "./ReporterContent";

const imagePath = "/meta/reporter.png";

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
    return <Image src={getImageFromServerSrc(imagePath)} alt={reporterName} maxW="150px" />;
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
