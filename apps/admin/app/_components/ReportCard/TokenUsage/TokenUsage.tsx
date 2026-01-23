import { Tooltip } from "@/components/ui/tooltip";
import type { Report } from "@/type";
import { IconButton, Text, VStack } from "@chakra-ui/react";
import { InfoIcon } from "lucide-react";
import { analysisInfo } from "./analysisInfo";

type Props = {
  report: Report;
};

export function TokenUsage({ report }: Props) {
  const info = analysisInfo(report);

  return (
    <Tooltip
      showArrow
      closeOnPointerDown={false}
      closeOnClick={false}
      openDelay={100}
      closeDelay={100}
      content={
        <VStack alignItems="flex-start">
          {info.hasInput ? (
            <>
              <Text>入力トークン/{info.tokenUsageInput}</Text>
              <Text>出力トークン/{info.tokenUsageOutput}</Text>
            </>
          ) : (
            <Text>トークン使用量/{info.tokenUsageTotal}</Text>
          )}
          <Text>推定コスト/{info.estimatedCost}</Text>
        </VStack>
      }
    >
      <IconButton variant="ghost" size="lg" aria-label="トークン使用量の詳細を表示">
        <InfoIcon />
      </IconButton>
    </Tooltip>
  );
}
