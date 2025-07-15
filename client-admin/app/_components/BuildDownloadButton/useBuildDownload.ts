"use client";

import { toaster } from "@/components/ui/toaster";
import { useState } from "react";

export function useBuildDownload() {
  const [isLoading, setIsLoading] = useState(false);

  async function handleDownload(slugs: string[] = [""]) {
    setIsLoading(true);

    try {
      const res = await fetch("/api/download", {
        method: "POST",
        body: JSON.stringify({ slugs: slugs.join(",") }),
      });

      if (!res.ok) {
        throw new Error("ビルドに失敗しました");
      }

      const blob = await res.blob();
      const contentDisposition = res.headers.get("Content-Disposition");
      const match = contentDisposition?.match(/filename="?(.+)"?/);
      const filename = match?.[1] ?? "kouchou-ai.zip";

      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (error) {
      throw new Error(`ダウンロードに失敗しました: ${error instanceof Error ? error.message : "不明なエラー"}`);
    } finally {
      setIsLoading(false);
    }
  }

  function exportStaticHTML(slug: string[]) {
    toaster.promise(handleDownload(slug), {
      success: {
        title: "HTML書き出し完了",
        description: "ダウンロードフォルダに保存されました。",
      },
      error: {
        title: "HTML書き出し失敗",
        description: "問題が解決しない場合は、管理者に問い合わせてください。",
      },
      loading: {
        title: "HTML書き出し中",
      },
    });
  }

  return {
    isLoading,
    exportStaticHTML,
  };
}
