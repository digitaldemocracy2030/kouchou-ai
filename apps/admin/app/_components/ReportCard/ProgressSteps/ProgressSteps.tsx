import { Box, Center, Steps } from "@chakra-ui/react";
import { Check, TriangleAlert } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { Processing } from "./Processing";
import { useReportProgressPoll } from "./useReportProgressPolling";

const steps = [
  { key: "extraction", title: "抽出" },
  { key: "embedding", title: "埋め込み" },
  { key: "hierarchical_clustering", title: "意見グループ化" },
  { key: "hierarchical_initial_labelling", title: "初期ラベリング" },
  { key: "hierarchical_merge_labelling", title: "統合ラベリング" },
  { key: "hierarchical_overview", title: "概要生成" },
  { key: "hierarchical_aggregation", title: "集約" },
  { key: "hierarchical_visualization", title: "可視化" },
] as const;

export const stepKeys = steps.map(({ key }) => key);

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

type Props = {
  slug: string;
};

export const ProgressSteps = ({ slug }: Props) => {
  const { progress, isError } = useReportProgressPoll(slug);

  const isLoading = progress === "loading";
  const isCompleted = progress === "completed";
  const currentStepIndex = isCompleted ? steps.length : isLoading ? 0 : stepKeys.indexOf(progress);
  const status = isError ? "error" : "processing";
  const router = useRouter();

  useEffect(() => {
    if (isCompleted || isError) {
      setTimeout(() => {
        router.refresh();
      }, 1000); // 直後だとデータが更新されていないので、1秒後に再取得する
    }
  }, [isCompleted, isError, router]);

  return (
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
  );
};
