"use client";

import { Button } from "@chakra-ui/react";
import { useBuildDownload } from "./useBuildDownload";

export const BuildDownloadButton = () => {
  const { isLoading, exportStaticHTML } = useBuildDownload();

  return (
    <Button size="xl" onClick={() => exportStaticHTML([""])} loading={isLoading} loadingText="エクスポート中">
      全レポートをエクスポート
    </Button>
  );
};
