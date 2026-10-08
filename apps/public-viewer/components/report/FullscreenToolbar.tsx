import { Tooltip } from "@/components/ui/tooltip";
import { Button, HStack, Icon } from "@chakra-ui/react";
import { Minimize2 } from "lucide-react";
import type { ReactNode } from "react";

type Props = {
  onExitFullscreen: () => void;
  /** 「全画面終了」の左側に並べる追加の操作（クラスタ粒度の切替など） */
  children?: ReactNode;
};

/**
 * 全画面表示の上部ツールバー。
 * id="fullScreenButtons" は ScatterChart が Plotly のモードバーを退避させる際に参照する。
 * 追加の操作は children として受け取り、右端の「全画面終了」は常に残す。
 */
export function FullscreenToolbar({ onExitFullscreen, children }: Props) {
  return (
    <HStack id="fullScreenButtons" w="100%" justifyContent="space-between" gap={2} p={2} flexShrink={0}>
      <HStack flex="1" minW={0} gap={2} overflowX="auto">
        {children}
      </HStack>
      <Tooltip content={"全画面終了"} openDelay={0} closeDelay={0}>
        <Button aria-label="全画面終了" onClick={onExitFullscreen} h="44px" borderWidth={2} flexShrink={0}>
          <Icon>
            <Minimize2 />
          </Icon>
        </Button>
      </Tooltip>
    </HStack>
  );
}
