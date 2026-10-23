import type { Report } from "@/type";
import { Box, Center, Code, Steps, Text, VStack } from "@chakra-ui/react";
import { Check, TriangleAlert } from "lucide-react";
import { useIsPresent } from "motion/react";
import { useRouter } from "next/navigation";
import { useEffect, useRef } from "react";
import { Processing } from "./Processing";
import { stepKeys, steps } from "./progressStepsConfig";
import { useReportProgressPoll } from "./useReportProgressPolling";

const stepItemstyle = {
  error: {
    completed: "font.error",
    processing: "bg.error",
    currentStepIcon: <TriangleAlert />,
  },
  processing: {
    completed: "font.processing",
    processing: "bg.processing",
    currentStepIcon: <Processing />,
  },
} as const;

// 直後だとデータが更新されていないので、最初の再取得は 1 秒後に行い、その後は間隔を空けて繰り返す
const FIRST_REFRESH_DELAY_MS = 1000;
const REFRESH_INTERVAL_MS = 3000;
// 一覧の取得は ready の全レポートの結果ファイルを読むので重い。成果物のアップロードはふつう 2 分以内に終わるので、
// 最初の 40 回（約 2 分）は 3 秒おき、その後は間隔を倍々に延ばして最大 30 秒おきにする
const FAST_REFRESH_COUNT = 40;
const MAX_REFRESH_INTERVAL_MS = 30_000;
// 大きな成果物のアップロード（Blob 運用）は 2 分を超えることがあるので、回数ではなく completed / error を
// 受けてからの経過時間で打ち切る。processing のまま固まったカード（サーバーの再起動など）が取り直しを
// 永久に続けないよう、上限は 30 分にする
const MAX_REFRESH_DURATION_MS = 30 * 60_000;

function refreshDelayMs(refreshCount: number): number {
  if (refreshCount === 0) return FIRST_REFRESH_DELAY_MS;
  if (refreshCount < FAST_REFRESH_COUNT) return REFRESH_INTERVAL_MS;
  return Math.min(REFRESH_INTERVAL_MS * 2 ** (refreshCount - FAST_REFRESH_COUNT + 1), MAX_REFRESH_INTERVAL_MS);
}

type Props = {
  slug: string;
  reportStatus: Report["status"];
};

export const ProgressSteps = ({ slug, reportStatus }: Props) => {
  const { progress, isError, errorMessage, errorLogExcerpt, restartPolling } = useReportProgressPoll(slug);

  const isLoading = progress === "loading";
  const isCompleted = progress === "completed";
  const resolvedStepIndex = isLoading || isCompleted || progress === "error" ? -1 : stepKeys.indexOf(progress);
  const currentStepIndex = isCompleted ? steps.length : Math.max(resolvedStepIndex, 0);
  const status = isError ? "error" : "processing";
  const router = useRouter();
  // カードが ready になっても、退場アニメーションの間は古い reportStatus（processing）のまま残る。
  // 非表示のタブではアニメーションが進まず長く残るので、その間は取り直さない
  const isPresent = useIsPresent();
  // effect が張り直されても間隔と上限が効くよう、取り直した回数と始めた時刻は ref で持つ
  const refreshCountRef = useRef(0);
  const refreshStartedAtRef = useRef<number | null>(null);

  // step-json は analysis-core の status ファイルを見て completed / error を返すが、カードの status（一覧）は
  // API が analysis-core の終了を待ち、成果物をストレージへ同期してから ready / error になる。そのため、
  // カードが processing の間は一覧を取り直し続ける。error のカードにも ProgressSteps は残るので、processing の間に限る
  useEffect(() => {
    if (!(isCompleted || isError) || reportStatus !== "processing" || !isPresent) return;

    refreshStartedAtRef.current ??= Date.now();
    const startedAt = refreshStartedAtRef.current;
    let timer: ReturnType<typeof setTimeout> | undefined;
    const scheduleRefresh = () => {
      const delay = refreshDelayMs(refreshCountRef.current);
      if (Date.now() + delay - startedAt > MAX_REFRESH_DURATION_MS) return;
      timer = setTimeout(() => {
        refreshCountRef.current += 1;
        router.refresh();
        scheduleRefresh();
      }, delay);
    };
    scheduleRefresh();

    return () => clearTimeout(timer);
  }, [isCompleted, isError, reportStatus, isPresent, router]);

  // completed の後にカードが error になった（成果物のアップロード失敗など）ら、step-json を取り直してエラー理由を表示する
  useEffect(() => {
    if (isCompleted && reportStatus === "error") {
      restartPolling();
    }
  }, [isCompleted, reportStatus, restartPolling]);

  return (
    <VStack align="stretch" gap="3">
      <Steps.Root step={currentStepIndex} count={steps.length} bg={stepItemstyle[status].processing} mt="2" p="6">
        <Steps.List gap="2">
          {steps.map((step, index) => (
            <Steps.Item key={step.key} index={index} gap="2" flex="auto" textStyle="body/sm">
              {index < currentStepIndex ? (
                <>
                  <Center w="6" h="6" bg={stepItemstyle[status].completed} borderRadius="full">
                    <Check size="16" color="white" />
                  </Center>
                  <Steps.Title textStyle="body/sm" color="font.primary">
                    {step.title}
                  </Steps.Title>
                </>
              ) : index === currentStepIndex ? (
                <>
                  <Box color={stepItemstyle[status].completed}>{stepItemstyle[status].currentStepIcon}</Box>
                  <Steps.Title
                    textStyle={isError ? "body/sm/bold" : "body/sm"}
                    color={isError ? "font.error" : "font.primary"}
                  >
                    {step.title}
                  </Steps.Title>
                </>
              ) : (
                <>
                  <Center w="6" h="6" bg={stepItemstyle[status].completed} opacity="0.16" borderRadius="full" />
                  <Steps.Title textStyle="body/sm" color={isError ? "font.secondary" : "font.primary"}>
                    {step.title}
                  </Steps.Title>
                </>
              )}
              <Steps.Separator m="0" bg="blackAlpha.500" h="1px" />
            </Steps.Item>
          ))}
        </Steps.List>
      </Steps.Root>
      {isError && (errorMessage || errorLogExcerpt) && (
        <Box bg="bg.error" borderRadius="md" px="4" py="3" role="alert" aria-live="assertive">
          {errorMessage && (
            <Text textStyle="body/sm/bold" color="font.error">
              {errorMessage}
            </Text>
          )}
          {errorLogExcerpt && (
            <Code display="block" mt="3" p="3" whiteSpace="pre-wrap" fontSize="xs" colorPalette="red" overflowX="auto">
              {errorLogExcerpt}
            </Code>
          )}
        </Box>
      )}
    </VStack>
  );
};
