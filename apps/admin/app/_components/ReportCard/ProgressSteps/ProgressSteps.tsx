import type { Report } from "@/type";
import { Box, Center, Code, Steps, Text, VStack } from "@chakra-ui/react";
import { Check, TriangleAlert } from "lucide-react";
import { useIsPresent } from "motion/react";
import { useRouter } from "next/navigation";
import { useEffect, useRef } from "react";
import { Processing } from "./Processing";
import { resolveDisplaySteps } from "./progressStepsConfig";
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
// 一覧の取得は ready の全レポートの結果ファイルを読むので、取り直しは約 2 分で打ち切る
const MAX_REFRESH_COUNT = 40;

type Props = {
  slug: string;
  reportStatus: Report["status"];
};

export const ProgressSteps = ({ slug, reportStatus }: Props) => {
  const { progress, plannedSteps, isError, errorMessage, errorLogExcerpt, restartPolling } =
    useReportProgressPoll(slug);

  const isLoading = progress === "loading";
  const isCompleted = progress === "completed";
  const currentStep = isLoading || isCompleted || progress === "error" ? null : progress;
  const steps = resolveDisplaySteps(plannedSteps, currentStep);
  // 工程を受け取る前に失敗した（状況の取得自体の失敗など）ときは、どの工程にも失敗マークを付けない
  const currentStepIndex = isCompleted
    ? steps.length
    : currentStep
      ? steps.findIndex((step) => step.key === currentStep)
      : isError
        ? -1
        : 0;
  const status = isError ? "error" : "processing";
  const router = useRouter();
  // カードが ready になっても、退場アニメーションの間は古い reportStatus（processing）のまま残る。
  // 非表示のタブではアニメーションが進まず長く残るので、その間は取り直さない
  const isPresent = useIsPresent();
  // effect が張り直されても上限が効くよう、取り直した回数は ref で数える
  const refreshCountRef = useRef(0);

  // step-json は analysis-core の status ファイルを見て completed / error を返すが、カードの status（一覧）は
  // API が analysis-core の終了を待ち、成果物をストレージへ同期してから ready / error になる。そのため、
  // カードが processing の間は一覧を取り直し続ける。error のカードにも ProgressSteps は残るので、processing の間に限る
  useEffect(() => {
    if (!(isCompleted || isError) || reportStatus !== "processing" || !isPresent) return;

    let timer: ReturnType<typeof setTimeout> | undefined;
    const scheduleRefresh = () => {
      if (refreshCountRef.current >= MAX_REFRESH_COUNT) return;
      const delay = refreshCountRef.current === 0 ? FIRST_REFRESH_DELAY_MS : REFRESH_INTERVAL_MS;
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
            <Steps.Item
              key={step.key}
              index={index}
              gap="2"
              flex="auto"
              textStyle="body/sm"
              data-testid="progress-step"
              data-step-key={step.key}
              data-step-state={
                index < currentStepIndex
                  ? "completed"
                  : index === currentStepIndex
                    ? isError
                      ? "failed"
                      : "current"
                    : "pending"
              }
            >
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
