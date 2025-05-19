import { Box, Checkbox, Flex, Input, Text } from "@chakra-ui/react";
import { ChangeEvent, useCallback } from "react";

type NumericRangeFilterItemProps = {
  attr: string;
  range: [number, number];
  fullRange: [number, number];
  isEnabled: boolean;
  includeEmpty: boolean;
  onRangeChange: (attr: string, range: [number, number]) => void;
  onToggleEnabled: (attr: string, isEnabled: boolean) => void;
  onToggleIncludeEmpty: (attr: string, include: boolean) => void;
};

export function NumericRangeFilterItem({
  attr,
  range,
  fullRange,
  isEnabled,
  includeEmpty,
  onRangeChange,
  onToggleEnabled,
  onToggleIncludeEmpty,
}: NumericRangeFilterItemProps) {
  const handleMinChange = useCallback(
    (value: number) => {
      onRangeChange(attr, [Math.min(value, range[1]), range[1]]);
    },
    [attr, range, onRangeChange]
  );

  const handleMaxChange = useCallback(
    (value: number) => {
      onRangeChange(attr, [range[0], Math.max(value, range[0])]);
    },
    [attr, range, onRangeChange]
  );

  return (
    <Box pl={2} pr={4} borderWidth={1} borderRadius="md" p={2}>
      <Flex align="center">
        <Checkbox
          isChecked={includeEmpty}
          onChange={() => onToggleIncludeEmpty(attr, !includeEmpty)}
          disabled={!isEnabled}
          mr={4}
        >
          空の値を含める
        </Checkbox>
        <Text fontSize="xs" width="60px" textAlign="right" mr={2}>
          最小: {fullRange[0] ?? "-"}
        </Text>
        <Input
          type="number"
          value={range[0] ?? ""}
          onChange={(e: ChangeEvent<HTMLInputElement>) => handleMinChange(Number(e.target.value))}
          size="sm"
          width="100px"
          disabled={!isEnabled}
        />
        <Text mx={2}>～</Text>
        <Input
          type="number"
          value={range[1] ?? ""}
          onChange={(e: ChangeEvent<HTMLInputElement>) => handleMaxChange(Number(e.target.value))}
          size="sm"
          width="100px"
          disabled={!isEnabled}
        />
        <Text fontSize="xs" width="60px" textAlign="left" ml={2}>
          最大: {fullRange[1] ?? "-"}
        </Text>
      </Flex>
    </Box>
  );
}
