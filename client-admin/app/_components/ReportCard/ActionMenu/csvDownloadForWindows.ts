import { csvDownloadCommon } from "./csvDownloadCommon";

export async function csvDownloadForWindows(slug: string) {
  return csvDownloadCommon(slug, {
    includeBOM: true,
    filenameSuffix: "_excel",
    contentType: "text/csv;charset=utf-8",
  });
}
