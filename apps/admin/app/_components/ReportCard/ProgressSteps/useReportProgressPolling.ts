import { useEffect, useState } from "react";
import type { stepKeys } from "./ProgressSteps";

type Progress = (typeof stepKeys)[number] | "loading" | "completed" | "error";
type StepJsonResponse = {
  status?: string;
  current_step?: string;
  error_message?: string | null;
  error_log_excerpt?: string | null;
};

function isProgress(value: string): value is Progress {
  return value === "loading" || value === "completed" || value === "error" || stepKeys.includes(value as (typeof stepKeys)[number]);
}

export function useReportProgressPoll(slug: string) {
  const [progress, setProgress] = useState<Progress>("loading");
  const [isError, setIsError] = useState<boolean>(false);
  const [isPolling, setIsPolling] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [errorLogExcerpt, setErrorLogExcerpt] = useState<string | null>(null);

  useEffect(() => {
    if (!isPolling) return;

    let cancelled = false;
    let retryCount = 0;
    const maxRetries = 10;

    async function poll() {
      if (cancelled) return;

      try {
        const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASEPATH}/admin/reports/${slug}/status/step-json`, {
          headers: {
            "x-api-key": process.env.NEXT_PUBLIC_ADMIN_API_KEY || "",
            "Content-Type": "application/json",
            // キャッシュを防止するためのヘッダーを追加
            "Cache-Control": "no-cache, no-store, must-revalidate",
            Pragma: "no-cache",
          },
        });

        if (response.ok) {
          const data = (await response.json()) as StepJsonResponse;

          if (!data.current_step || data.current_step === "loading") {
            retryCount = 0;
            setTimeout(poll, 3000);
            return;
          }

          if (isProgress(data.current_step)) {
            setProgress(data.current_step);
          }

          if (data.status === "error") {
            setErrorMessage(data.error_message || "レポート生成に失敗しました。");
            setErrorLogExcerpt(data.error_log_excerpt || null);
            setIsError(true);
            setIsPolling(false);
            return;
          }

          if (data.current_step === "completed") {
            setIsPolling(false);
            return;
          }

          // 正常なレスポンスの場合は次のポーリングをスケジュール
          setTimeout(poll, 3000);
        } else {
          retryCount++;
          if (retryCount >= maxRetries) {
            console.error("Maximum retry attempts reached");
            setErrorMessage("レポート生成状況の取得に失敗しました。");
            setIsError(true);
            setIsPolling(false);
            return;
          }
          const retryInterval = retryCount < 3 ? 2000 : 5000;
          setTimeout(poll, retryInterval);
        }
      } catch (error) {
        console.error("Polling error:", error);
        retryCount++;
        if (retryCount >= maxRetries) {
          setErrorMessage("レポート生成状況の取得に失敗しました。");
          setIsError(true);
          setIsPolling(false);
          return;
        }
        setTimeout(poll, 5000);
      }
    }

    poll();

    return () => {
      cancelled = true;
    };
  }, [slug, isPolling]);

  return { progress, isError, errorMessage, errorLogExcerpt };
}
