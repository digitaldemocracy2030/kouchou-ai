import { useCallback, useEffect, useState } from "react";

// "loading" / "completed" / "error" 以外は analysis-core の工程名（分析方式によって変わるので string で持つ）
type Progress = string;
type StepJsonResponse = {
  status?: string;
  current_step?: string;
  steps?: string[] | null;
  error_message?: string | null;
  error_log_excerpt?: string | null;
};

function toPlannedSteps(value: unknown): string[] | null {
  if (!Array.isArray(value)) return null;
  const steps = value.filter((step): step is string => typeof step === "string" && step.length > 0);
  return steps.length > 0 ? steps : null;
}

export function useReportProgressPoll(slug: string) {
  const [progress, setProgress] = useState<Progress>("loading");
  const [plannedSteps, setPlannedSteps] = useState<string[] | null>(null);
  const [isError, setIsError] = useState<boolean>(false);
  const [isPolling, setIsPolling] = useState<boolean>(true);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [errorLogExcerpt, setErrorLogExcerpt] = useState<string | null>(null);

  useEffect(() => {
    if (!isPolling) return;

    const encodedSlug = encodeURIComponent(slug);
    let cancelled = false;
    let retryCount = 0;
    const maxRetries = 10;

    async function poll() {
      if (cancelled) return;

      try {
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_BASEPATH}/admin/reports/${encodedSlug}/status/step-json`,
          {
            headers: {
              "x-api-key": process.env.NEXT_PUBLIC_ADMIN_API_KEY || "",
              "Content-Type": "application/json",
              // キャッシュを防止するためのヘッダーを追加
              "Cache-Control": "no-cache, no-store, must-revalidate",
              Pragma: "no-cache",
            },
          },
        );

        if (response.ok) {
          const data = (await response.json()) as StepJsonResponse;

          const isLoadingStep = !data.current_step || data.current_step === "loading";

          // 工程が始まる前の失敗（current_job が無いまま error）も、loading として待ち続けずにエラーを出す
          if (isLoadingStep && data.status !== "error") {
            retryCount = 0;
            setTimeout(poll, 3000);
            return;
          }

          // 失敗した工程が分からないときは "error" にし、どの工程にも失敗マークを付けない
          setProgress(isLoadingStep ? "error" : (data.current_step as string));
          const steps = toPlannedSteps(data.steps);
          if (steps) {
            setPlannedSteps(steps);
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

  // completed / error で止めたポーリングをもう一度始める（completed の後にレポートが error になった時に理由を取り直す）
  const restartPolling = useCallback(() => setIsPolling(true), []);

  return { progress, plannedSteps, isError, errorMessage, errorLogExcerpt, restartPolling };
}
