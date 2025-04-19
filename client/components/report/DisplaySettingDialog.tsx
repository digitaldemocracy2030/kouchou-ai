import {
  DialogBody,
  DialogCloseTrigger,
  DialogContent,
  DialogFooter,
  DialogRoot
} from "@/components/ui/dialog";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { Box, Button, HStack, Spacer, Text } from "@chakra-ui/react";
import { useState } from "react";

type Props = {
  onClose: () => void;
  onChangeFilter: (maxDensity: number, minValue: number) => void;
  currentMaxDensity: number;
  currentMinValue: number;
  showClusterLabels?: boolean;
  onToggleClusterLabels?: (show: boolean) => void;
};

export function DisplaySettingDialog({
  onClose,
  onChangeFilter,
  currentMaxDensity,
  currentMinValue,
  showClusterLabels = false,
  onToggleClusterLabels,
}: Props) {
  const [maxDensity, setMaxDensity] = useState(currentMaxDensity);
  const [minValue, setMinValue] = useState(currentMinValue);

  function onApply() {
    onChangeFilter(maxDensity, minValue);
    onClose();
  }

  return (
    <DialogRoot lazyMount open={true} onOpenChange={onClose}>
      <DialogContent>
        <DialogBody>
          {/* 全体に影響する設定 */}
          <Box mb={6} mt={4}>
            <Text fontWeight="bold" mb={2} fontSize="md">表示設定</Text>
            <Text fontSize="sm" mb={5}>
              「全体図」および「濃い意見グループ」に関する設定項目です。
            </Text>
            <Box 
              p={2} 
              borderRadius="md" 
              borderWidth="1px" 
              borderColor="gray.200"
              mb={2}
            >
              <HStack gap={2} alignItems="center">
                <Text fontSize="sm">意見グループ名を表示</Text>
                <Spacer />
                <Switch 
                  checked={showClusterLabels} 
                  onChange={() => onToggleClusterLabels?.(!showClusterLabels)}
                  size="sm"
                />
              </HStack>
            </Box>
          </Box>

          {/* 区切り線 */}
          <Box borderBottom="1px solid" borderColor="gray.200" mb={6} />

          {/* 濃い意見グループに関する設定 */}
          <Box mb={4}>
            <Text fontWeight="bold" mb={2} fontSize="md">濃い意見グループ設定</Text>
            <Text fontSize="sm" mb={5}>
              「濃い意見グループ」に関する設定項目です。
            </Text>
            <Slider
              label={`上位何％の意見グループを表示するか: ${maxDensity * 100}%`}
              step={0.1}
              min={0.1}
              max={1}
              value={[maxDensity]}
              onValueChange={(e) => setMaxDensity(Number(e.value[0]))}
              marks={[
                { value: 0.1, label: "10%" },
                { value: 1, label: "100%" },
              ]}
            />
          </Box>
          <Box>
            <Slider
              label={`意見グループのサンプル数の最小数: ${minValue}`}
              step={1}
              min={0}
              max={10}
              value={[minValue]}
              onValueChange={(e) => setMinValue(Number(e.value[0]))}
              marks={[
                { value: 0, label: "0" },
                { value: 10, label: "10" },
              ]}
            />
          </Box>
        </DialogBody>
        <DialogFooter justifyContent={"space-between"}>
          <Spacer />
          <Box>
            <Button onClick={onApply}>設定を適用</Button>
          </Box>
        </DialogFooter>
        <DialogCloseTrigger />
      </DialogContent>
    </DialogRoot>
  );
}
