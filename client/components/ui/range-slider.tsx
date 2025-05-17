import { Box, Slider as ChakraSlider } from "@chakra-ui/react";
import * as React from "react";

interface RangeSliderProps {
  min: number;
  max: number;
  step?: number;
  defaultValue?: [number, number];
  value?: [number, number];
  onChange?: (value: [number, number]) => void;
  "aria-label"?: string[];
  mb?: number;
}

export function RangeSlider(props: RangeSliderProps) {
  const { min, max, step = 1, defaultValue, value, onChange, mb } = props;
  const [localValue, setLocalValue] = React.useState<[number, number]>(value || defaultValue || [min, max]);

  React.useEffect(() => {
    if (value) {
      setLocalValue(value);
    }
  }, [value]);

  const handleChange = (newValue: number, index: number) => {
    const newValues = [...localValue] as [number, number];
    newValues[index] = newValue;

    // 最小値は最大値を超えられないし、最大値は最小値を下回れない
    if (index === 0 && newValues[0] > newValues[1]) {
      newValues[0] = newValues[1];
    } else if (index === 1 && newValues[1] < newValues[0]) {
      newValues[1] = newValues[0];
    }

    setLocalValue(newValues);
    onChange?.(newValues);
  };

  return (
    <Box mb={mb}>
      <Box position="relative" pb={6}>
        <Box position="relative" height="24px">
          {/* First Thumb - Min Value */}
          <ChakraSlider
            aria-label={props["aria-label"]?.[0] || "min"}
            min={min}
            max={max}
            step={step}
            value={localValue[0]}
            onChange={(val) => handleChange(val, 0)}
            position="absolute"
            width="100%"
            zIndex={2}
          >
            <ChakraSlider.Control>
              <ChakraSlider.Track>
                <ChakraSlider.Range start={0} end={((localValue[0] - min) / (max - min)) * 100} bg="gray.200" />
              </ChakraSlider.Track>
              <ChakraSlider.Thumb zIndex={2} />
            </ChakraSlider.Control>
          </ChakraSlider>

          {/* Second Thumb - Max Value */}
          <ChakraSlider
            aria-label={props["aria-label"]?.[1] || "max"}
            min={min}
            max={max}
            step={step}
            value={localValue[1]}
            onChange={(val) => handleChange(val, 1)}
            position="absolute"
            width="100%"
            zIndex={1}
          >
            <ChakraSlider.Control>
              <ChakraSlider.Track>
                <ChakraSlider.Range
                  start={((localValue[0] - min) / (max - min)) * 100}
                  end={((localValue[1] - min) / (max - min)) * 100}
                  bg="blue.500"
                />
              </ChakraSlider.Track>
              <ChakraSlider.Thumb zIndex={2} />
            </ChakraSlider.Control>
          </ChakraSlider>
        </Box>
      </Box>
    </Box>
  );
}

// 内部コンポーネントエクスポート（互換性のため）
RangeSlider.Track = function RangeSliderTrack({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
};

RangeSlider.FilledTrack = function RangeSliderFilledTrack() {
  return null; // 実際の描画は親コンポーネントで行う
};

RangeSlider.Thumb = function RangeSliderThumb() {
  return null; // 実際の描画は親コンポーネントで行う
};
