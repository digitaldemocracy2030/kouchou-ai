import { csvDownloadCommon } from "./csvDownloadCommon";

export async function csvDownload(slug: string) {
  return csvDownloadCommon(slug);
}
