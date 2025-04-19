import { RadioCardItem, RadioCardRoot } from "@/components/ui/radio-card";
import { Tooltip } from "@/components/ui/tooltip";
import { Button, HStack, Icon, useBreakpointValue } from "@chakra-ui/react";
import {
  ChartScatterIcon,
  CogIcon,
  FullscreenIcon,
  MessageCircleWarningIcon,
  SquareSquareIcon,
} from "lucide-react";
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
  return (
    <HStack
      w={"100%"}
      maxW={"1200px"}
      mx={"auto"}
      justify={"space-between"}
      align={"center"}
      mb={2}
    >
      <RadioCardRoot
        orientation="horizontal"
        align="center"
        justify="center"
        w={"100%"}
        maxW={"xl"}
        size={"sm"}
        display={"block"}
        value={selected}
        onChange={(e: React.ChangeEvent<HTMLInputElement>) =>
          onChange(e.target.value)
        }
        colorPalette={"cyan"}
      >
        <HStack align={"stretch"}>
          <RadioCardItem
            value={"scatterAll"}
            label={useBreakpointValue({ base: "", md: "全体図" })}
            indicator={false}
            icon={
              <Icon>
                <ChartScatterIcon />
              </Icon>
            }
            cursor={"pointer"}
          />
          <RadioCardItem
            value={"scatterDensity"}
            label={useBreakpointValue({ base: "", md: "濃い意見グループ" })}
            indicator={false}
            icon={
              <Icon>
                <MessageCircleWarningIcon />
              </Icon>
            }
            cursor={"pointer"}
            disabled={!isDenseGroupEnabled}
            disabledReason={"この設定条件では抽出できませんでした"}
          />
          <RadioCardItem
            value={"treemap"}
            label={useBreakpointValue({ base: "", md: "階層図" })}
            indicator={false}
            icon={
              <Icon>
                <SquareSquareIcon />
              </Icon>
            }
            cursor={"pointer"}
          />
        </HStack>
      </RadioCardRoot>
      <HStack>
        <Tooltip content={"表示設定"} openDelay={0} closeDelay={0}>
          <Button
            onClick={onClickDensitySetting}
            variant={"outline"}
            h={"50px"}
          >
            <Icon>
              <CogIcon />
            </Icon>
          </Button>
        </Tooltip>
        <Tooltip content={"全画面表示"} openDelay={0} closeDelay={0}>
          <Button onClick={onClickFullscreen} variant={"outline"} h={"50px"}>
            <Icon>
              <FullscreenIcon />
            </Icon>
          </Button>
        </Tooltip>
      </HStack>
    </HStack>
  );
}
