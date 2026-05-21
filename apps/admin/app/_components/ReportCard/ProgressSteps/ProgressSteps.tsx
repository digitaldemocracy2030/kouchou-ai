import { Box, Center, Code, Steps, Text, VStack } from "@chakra-ui/react";
import { Check, TriangleAlert } from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
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

type Props = {
  slug: string;
};

export const ProgressSteps = ({ slug }: Props) => {
  const { progress, isError, errorMessage, errorLogExcerpt } = useReportProgressPoll(slug);

  const isLoading = progress === "loading";
  const isCompleted = progress === "completed";
  const resolvedStepIndex = isLoading || isCompleted || progress === "error" ? -1 : stepKeys.indexOf(progress);
  const currentStepIndex = isCompleted ? steps.length : Math.max(resolvedStepIndex, 0);
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
