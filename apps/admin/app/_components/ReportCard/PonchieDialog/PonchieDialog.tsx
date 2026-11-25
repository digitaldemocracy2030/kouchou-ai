"use client";

import { downloadFile } from "@/app/utils/downloadFile";
import { Button } from "@/components/ui/button";
import {
  DialogBody,
  DialogCloseTrigger,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogRoot,
  DialogTitle,
} from "@/components/ui/dialog";
import type { Report } from "@/type";
import { Image, Stack, Text } from "@chakra-ui/react";
import { useState } from "react";
import { generatePonchie } from "./generatePonchie";

export function PonchieDialog({ report, onClose }: { report: Report; onClose: () => void }) {
  const [data, setData] = useState<string>();
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function generate() {
    setBusy(true);
    setError("");
    try {
      const result = await generatePonchie(report.slug);
      if (result.ok) setData(result.data);
      else setError(result.error);
    } catch {
      setError("ポンチ絵を生成できませんでした。");
    } finally {
      setBusy(false);
    }
  }

  return (
    <DialogRoot size="lg" open onOpenChange={({ open }) => !open && !busy && onClose()} placement="center">
      <DialogContent>
        <DialogHeader>
          <DialogTitle>ポンチ絵を作る</DialogTitle>
        </DialogHeader>
        <DialogCloseTrigger disabled={busy} />
        <DialogBody>
          <Stack gap="3">
            <Text>{report.title}</Text>
            <Text fontSize="sm">
              レポートの題名・概要・主な論点を画像生成サービスに送ります。生成には API の利用料がかかります。
            </Text>
            {busy && <Text as="output">生成しています…</Text>}
            {error && (
              <Text role="alert" color="fg.error">
                {error}
              </Text>
            )}
            {data && (
              <>
                <Image
                  src={`data:image/png;base64,${data}`}
                  alt="生成した論点の概念図"
                  maxH="48vh"
                  objectFit="contain"
                />
                <Text fontSize="sm">文字や論点がレポートと一致することを確認してから使用してください。</Text>
              </>
            )}
          </Stack>
        </DialogBody>
        <DialogFooter>
          <Button variant="secondary" onClick={generate} loading={busy}>
            {data ? "再生成" : "生成"}
          </Button>
          {data && (
            <Button
              onClick={() =>
                downloadFile({ data, filename: `kouchou_${report.slug}_ponchie.png`, contentType: "image/png" })
              }
            >
              PNG をダウンロード
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </DialogRoot>
  );
}
