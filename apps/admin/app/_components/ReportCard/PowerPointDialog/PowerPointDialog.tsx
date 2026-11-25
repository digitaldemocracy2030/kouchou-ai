"use client";

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
import { Stack, Text } from "@chakra-ui/react";
import { useState } from "react";
import type { CoverImage } from "./createPowerPoint";
import { loadDeckData } from "./loadDeckData";

async function readCover(file: File): Promise<CoverImage> {
  if (!["image/png", "image/jpeg"].includes(file.type) || file.size > 8 * 1024 * 1024) {
    throw new Error("表紙画像には 8 MB 以下の PNG または JPEG を選んでください。");
  }
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const data = String(reader.result);
      const image = new Image();
      image.onload = () => resolve({ data, width: image.naturalWidth, height: image.naturalHeight });
      image.onerror = () => reject(new Error("表紙画像を読み込めませんでした。"));
      image.src = data;
    };
    reader.onerror = () => reject(new Error("表紙画像を読み込めませんでした。"));
    reader.readAsDataURL(file);
  });
}

export function PowerPointDialog({ report, onClose }: { report: Report; onClose: () => void }) {
  const [coverFile, setCoverFile] = useState<File>();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  async function download() {
    setBusy(true);
    setError("");
    try {
      const cover = coverFile && (await readCover(coverFile));
      const [{ createPowerPoint, makeReportUrl }, result] = await Promise.all([
        import("./createPowerPoint"),
        loadDeckData(report.slug),
      ]);
      if (!result.ok) {
        setError(result.error);
        return;
      }
      const viewer = process.env.NEXT_PUBLIC_CLIENT_BASEPATH;
      const reportUrl =
        report.visibility === "public" && viewer
          ? makeReportUrl(viewer, window.location.origin, report.slug)
          : undefined;
      await createPowerPoint(result.data, reportUrl, cover).writeFile({ fileName: `kouchou_${report.slug}.pptx` });
      onClose();
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "PowerPoint を書き出せませんでした。");
    } finally {
      setBusy(false);
    }
  }

  return (
    <DialogRoot open onOpenChange={({ open }) => !open && !busy && onClose()} placement="center">
      <DialogContent>
        <DialogHeader>
          <DialogTitle>PowerPoint 書き出し</DialogTitle>
        </DialogHeader>
        <DialogCloseTrigger disabled={busy} />
        <DialogBody>
          <Stack gap="3">
            <Text>{report.title}</Text>
            <label>
              表紙画像（任意）
              <br />
              <input
                type="file"
                accept="image/png,image/jpeg"
                disabled={busy}
                onChange={(event) => setCoverFile(event.target.files?.[0])}
              />
            </label>
            <Text fontSize="sm">内容を確認したポンチ絵を表紙に入れられます。</Text>
            {error && (
              <Text role="alert" color="fg.error">
                {error}
              </Text>
            )}
          </Stack>
        </DialogBody>
        <DialogFooter>
          <Button onClick={download} loading={busy}>
            ダウンロード
          </Button>
        </DialogFooter>
      </DialogContent>
    </DialogRoot>
  );
}
