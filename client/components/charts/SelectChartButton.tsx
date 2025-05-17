import { AllViewIcon, DenseViewIcon, HierarchyViewIcon } from "@/components/icons/ViewIcons";
import { Tooltip } from "@/components/ui/tooltip";
import { Box, Button, HStack, Icon, SegmentGroup, Stack, useBreakpointValue } from "@chakra-ui/react";
import { CogIcon, FullscreenIcon } from "lucide-react";
import type React from "react";

type Props = {
  selected: string;
  onChange: (value: string) => void;
  onClickDensitySetting: () => void;
  onClickFullscreen: () => void;
  isDenseGroupEnabled: boolean;
};

export function SelectChartButton({
  selected,
  onChange,
  onClickDensitySetting,
  onClickFullscreen,
  isDenseGroupEnabled,
}: Props) {
  const isVertical = useBreakpointValue({ base: true, sm: true, md: false });
  const isMobile = useBreakpointValue({ base: true, sm: true, md: false });

  const items = [
    {
      value: "scatterAll",
      label: isVertical ? (
        <Stack direction="column" gap={1} alignItems="center" px={4} py={2}>
          <Icon as={AllViewIcon} w="1.5" h="1.5" />
          <Box
            color="gray.500"
            fontWeight={selected === "scatterAll" ? "bold" : "normal"}
            fontSize="2xs"
            lineHeight="1"
          >
            全体
          </Box>
        </Stack>
      ) : (
        <HStack>
          <Icon as={AllViewIcon} w="6" mr={3} />
          <Box color="gray.500" fontWeight={selected === "scatterAll" ? "bold" : "normal"} px={4} py={2}>
            全体
          </Box>
        </HStack>
      ),
      isDisabled: false,
    },
    {
      value: "scatterDensity",
      label: isVertical ? (
        <Stack direction="column" gap={1} alignItems="center" px={4} py={2}>
          <Icon as={DenseViewIcon} w="1.5" h="1.5" />
          <Box
            color="gray.500"
            fontWeight={selected === "scatterDensity" ? "bold" : "normal"}
            fontSize="2xs"
            lineHeight="1"
          >
            濃い意見
          </Box>
        </Stack>
      ) : (
        <HStack>
          <Icon as={DenseViewIcon} w="6" mr={3} />
          <Box color="gray.500" fontWeight={selected === "scatterDensity" ? "bold" : "normal"} px={4} py={2}>
            濃い意見
          </Box>
        </HStack>
      ),
      isDisabled: !isDenseGroupEnabled,
      tooltip: !isDenseGroupEnabled ? "この設定条件では抽出できませんでした" : undefined,
    },
    {
      value: "treemap",
      label: isVertical ? (
        <Stack direction="column" gap={1} alignItems="center" px={4} py={2}>
          <Icon as={HierarchyViewIcon} w="1.5" h="1.5" />
          <Box color="gray.500" fontWeight={selected === "treemap" ? "bold" : "normal"} fontSize="2xs" lineHeight="1">
            階層
          </Box>
        </Stack>
      ) : (
        <HStack>
          <Icon as={HierarchyViewIcon} w="6" mr={3} />
          <Box color="gray.500" fontWeight={selected === "treemap" ? "bold" : "normal"} px={4} py={2}>
            階層
          </Box>
        </HStack>
      ),
      isDisabled: false,
    },
  ];

  const handleChange = (event: React.FormEvent<HTMLDivElement>) => {
    const value = (event.target as HTMLInputElement).value;
    onChange(value);
  };

  return (
    <Box
      w={"100%"}
      maxW={"1200px"}
      mx={"auto"}
      mb={isMobile ? 16 : 2} // モバイル表示時は下部にボタンを配置するためのスペースを確保
      position="relative"
    >
      {/* セグメントグループを中央に配置 */}
      <Box w="100%" display="flex" justifyContent="center">
        <SegmentGroup.Root
          value={selected}
          onChange={handleChange}
          orientation={isVertical ? "vertical" : "horizontal"}
          size="md"
          bg="gray.100"
        >
          <SegmentGroup.Indicator bg="white" border="1px solid #E4E4E7" boxShadow="0 4px 6px 0 rgba(0, 0, 0, 0.1)" />
          <SegmentGroup.Items items={items} />
        </SegmentGroup.Root>
      </Box>

      {/* ボタンを配置（モバイル表示時は下部中央に配置） */}
      {isMobile ? (
        <Box position="absolute" bottom="-60px" left="0" right="0" display="flex" justifyContent="center" mt={4}>
          <HStack gap={2}>
            <Tooltip content={"表示設定"} openDelay={0} closeDelay={0}>
              <Button onClick={onClickDensitySetting} variant={"outline"} h={"40px"} w={"40px"} p={0}>
                <Icon as={CogIcon} boxSize={5} />
              </Button>
            </Tooltip>
            <Tooltip content={"全画面表示"} openDelay={0} closeDelay={0}>
              <Button onClick={onClickFullscreen} variant={"outline"} h={"40px"} w={"40px"} p={0}>
                <Icon as={FullscreenIcon} boxSize={5} />
              </Button>
            </Tooltip>
          </HStack>
        </Box>
      ) : (
        <Box position="absolute" right="0" top="0">
          <HStack gap={1}>
            <Tooltip content={"表示設定"} openDelay={0} closeDelay={0}>
              <Button onClick={onClickDensitySetting} variant={"outline"} h={"40px"} w={"40px"} p={0}>
                <Icon as={CogIcon} boxSize={5} />
              </Button>
            </Tooltip>
            <Tooltip content={"全画面表示"} openDelay={0} closeDelay={0}>
              <Button onClick={onClickFullscreen} variant={"outline"} h={"40px"} w={"40px"} p={0}>
                <Icon as={FullscreenIcon} boxSize={5} />
              </Button>
            </Tooltip>
          </HStack>
        </Box>
      )}
    </Box>
  );
}
