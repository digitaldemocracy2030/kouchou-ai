import { Box, Flex, Text } from "@chakra-ui/react";
import { useCallback } from "react";
import { Slider } from "@/components/ui/slider";
import { Checkbox } from "@/components/ui/checkbox";

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
  const handleRangeChange = useCallback(
    (value: number[]) => {
      if (value.length === 2) {
        onRangeChange(attr, [value[0], value[1]]);
      }
    },
    [attr, onRangeChange]
  );

  return (
    <Box pl={2} pr={4} borderWidth={1} borderRadius="md" p={2}>
      <Flex direction="column">
        <Checkbox
          inputProps={{
            checked: includeEmpty,
            disabled: !isEnabled,
            onChange: () => onToggleIncludeEmpty(attr, !includeEmpty)
          }}
          mb={2}
        >
          空の値を含める
        </Checkbox>
        <Flex direction="column">
          <Slider
            min={fullRange[0]}
            max={fullRange[1]}
            step={1}
            value={[range[0], range[1]]}
            onValueChange={(details) => handleRangeChange(Array.isArray(details.value) ? details.value : [details.value, details.value])}
            disabled={!isEnabled}
            marks={[
              { value: fullRange[0], label: `${fullRange[0]}` },
              { value: fullRange[1], label: `${fullRange[1]}` }
            ]}
          />
          <Flex justify="space-between" mt={1}>
            <Text fontSize="xs">{range[0]}</Text>
            <Text fontSize="xs">{range[1]}</Text>
          </Flex>
        </Flex>
      </Flex>
    </Box>
  );
}
