import { AllViewIcon, DenseViewIcon, HierarchyViewIcon } from "@/components/icons/ViewIcons";
import { Tooltip } from "@/components/ui/tooltip";
import { Box, Button, HStack, Icon, SegmentGroup, Stack } from "@chakra-ui/react";
import { CogIcon, Filter, FullscreenIcon } from "lucide-react"; // Filter アイコンをインポート
import type React from "react";
import type { ComponentType } from "react";

type Props = {
  selected: string;
  onChange: (value: string) => void;
  onClickDensitySetting: () => void;
  onClickFullscreen: () => void;
  isDenseGroupEnabled: boolean;
  onClickAttentionFilter?: () => void;
  isAttentionFilterEnabled?: boolean;
  showAttentionFilterBadge?: boolean;
  attentionFilterBadgeCount?: number;
};

const SegmentItemWithIcon = (icon: ComponentType, text: string, selected: boolean) => {
  return (
    <Stack
      direction={["column", null, "row"]}
      gap={2}
      alignItems="center"
      justifyContent="center"
      px={4}
      py={2}
      position="absolute"
      top={0}
      left={0}
      right={0}
      bottom={0}
      color="gray.500"
    >
      <Icon as={icon} />
      <Box fontSize={["14px", null, "16px"]} fontWeight={selected ? "bold" : "normal"} lineHeight="1" textWrap="nowrap">
        {text}
      </Box>
    </Stack>
  );
};

export function SelectChartButton({
  selected,
  onChange,
  onClickDensitySetting,
  onClickFullscreen,
  isDenseGroupEnabled,
  onClickAttentionFilter,
  isAttentionFilterEnabled,
  showAttentionFilterBadge,
  attentionFilterBadgeCount,
}: Props) {
  const items = [
    {
      value: "scatterAll",
      label: SegmentItemWithIcon(AllViewIcon, "全体", selected === "scatterAll"),
      isDisabled: false,
    },
    {
      value: "scatterDensity",
      label: SegmentItemWithIcon(DenseViewIcon, "濃い意見", selected === "scatterDensity"),
      isDisabled: !isDenseGroupEnabled,
      tooltip: !isDenseGroupEnabled ? "この設定条件では抽出できませんでした" : undefined,
    },
    {
      value: "treemap",
      label: SegmentItemWithIcon(HierarchyViewIcon, "階層", selected === "treemap"),
      isDisabled: false,
    },
  ];

  const handleChange = (event: React.FormEvent<HTMLDivElement>) => {
    const value = (event.target as HTMLInputElement).value;
    onChange(value);
  };

  return (
    <Box maxW="1200px" mx="auto" mb={2}>
      <Box display="grid" gridTemplateColumns={["1fr", null, "1fr auto"]} gap="3">
        <SegmentGroup.Root
          value={selected}
          onChange={handleChange}
          size="md"
          justifySelf={["center", null, "left", "center"]}
          ml={[0, null, null, "104px"]}
          w={["100%", null, "auto"]}
          h={["80px", null, "56px"]}
        >
          <SegmentGroup.Indicator bg="white" border="1px solid #E4E4E7" boxShadow="0 4px 6px 0 rgba(0, 0, 0, 0.1)" />
          <SegmentGroup.Items items={items} w={["calc(100% / 3)", null, "162px"]} h="100%" cursor="pointer" />
        </SegmentGroup.Root>

        <HStack gap={1} justifySelf={["end"]} alignSelf={"center"}>
          {isAttentionFilterEnabled && onClickAttentionFilter && (
            <Tooltip content={"フィルタ"} openDelay={0} closeDelay={0}>
              <Button onClick={onClickAttentionFilter} variant="outline" h={"50px"}>
                <Box display="flex" alignItems="center" gap={1}>
                  <Icon>
                    <Filter size={16} />
                  </Icon>
                  {showAttentionFilterBadge && (
                    <Box as="span" fontSize="xs" bg="cyan.500" color="white" p="1" borderRadius="md" minW="5">
                      {attentionFilterBadgeCount}
                    </Box>
                  )}
                </Box>
              </Button>
            </Tooltip>
          )}

          <Tooltip content={"表示設定"} openDelay={0} closeDelay={0}>
            <Button onClick={onClickDensitySetting} variant={"outline"} h={"50px"} w={"50px"} p={0}>
              <Icon as={CogIcon} />
            </Button>
          </Tooltip>

          <Tooltip content={"全画面表示"} openDelay={0} closeDelay={0}>
            <Button onClick={onClickFullscreen} variant={"outline"} h={"50px"} w={"50px"} p={0}>
              <Icon as={FullscreenIcon} />
            </Button>
          </Tooltip>
        </HStack>
      </Box>
    </Box>
  );
}
