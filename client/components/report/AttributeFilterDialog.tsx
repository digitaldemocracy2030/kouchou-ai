import { Checkbox } from "@/components/ui/checkbox";
import { DialogBody, DialogContent, DialogFooter, DialogRoot } from "@/components/ui/dialog";
import { Box, Button, Flex, Heading, Text, Wrap, WrapItem } from "@chakra-ui/react";
import { ChangeEvent, useCallback, useMemo, useState } from "react";
import { NumericRangeFilterItem } from "./NumericRangeFilterItem";

export type AttributeFilters = Record<string, string[]>;
export type NumericRangeFilters = Record<string, [number, number]>;
type AttributeTypes = Record<string, "numeric" | "categorical">;

interface AttributeFilterDialogProps {
  onClose: () => void;
  onApplyFilters: (
    filters: AttributeFilters,
    numericRanges: NumericRangeFilters,
    includeEmpty: Record<string, boolean>,
    enabledRanges: Record<string, boolean>,
  ) => void;
  samples: Array<Record<string, string>>; // 全標本
  // 現在のフィルター状態
  initialFilters?: AttributeFilters;
  initialNumericRanges?: NumericRangeFilters;
  initialEnabledRanges?: Record<string, boolean>;
  initialIncludeEmptyValues?: Record<string, boolean>;
}

export function AttributeFilterDialog({
  onClose,
  onApplyFilters,
  samples,
  initialFilters = {},
  initialNumericRanges = {},
  initialEnabledRanges = {},
  initialIncludeEmptyValues = {},
}: AttributeFilterDialogProps) {
  // 属性名リスト
  const attributeNames = useMemo(() => {
    if (samples.length === 0) return [];
    return Object.keys(samples[0]);
  }, [samples]);

  // 属性ごとの値リスト
  const availableAttributes = useMemo(() => {
    const result: Record<string, string[]> = {};
    for (const attr of attributeNames) {
      // 空文字を除外し、値を昇順ソート
      result[attr] = Array.from(new Set(samples.map((s) => s[attr] ?? "")))
        .filter((v: string) => v !== "")
        .sort((a: string, b: string) => a.localeCompare(b, "ja"));
    }
    return result;
  }, [samples, attributeNames]);

  // 属性型判定
  const attributeTypes: AttributeTypes = useMemo(() => {
    const typeMap: AttributeTypes = {};
    for (const attr of attributeNames) {
      const values = availableAttributes[attr];
      // 空文字は除外して型判定
      const isNumeric = values.filter((v: string) => v.trim() !== "").every((v: string) => !Number.isNaN(Number(v)));
      typeMap[attr] = isNumeric && values.length > 0 ? "numeric" : "categorical";
    }
    return typeMap;
  }, [attributeNames, availableAttributes]);

  // 数値属性のmin/max
  const numericRangesAll = useMemo(() => {
    const ranges: NumericRangeFilters = {};
    for (const attr of attributeNames) {
      if (attributeTypes[attr] === "numeric") {
        // 空文字を除外して数値化
        const nums = availableAttributes[attr].filter((v: string) => v.trim() !== "").map(Number);
        if (nums.length > 0) {
          ranges[attr] = [Math.min(...nums), Math.max(...nums)];
        } else {
          ranges[attr] = [0, 0];
        }
      }
    }
    return ranges;
  }, [attributeNames, attributeTypes, availableAttributes]);

  // --- 状態 ---
  // カテゴリ属性: 選択値 (初期値を反映)
  const [categoricalFilters, setCategoricalFilters] = useState<AttributeFilters>(initialFilters);
  // 数値属性: レンジ (初期値を反映、ない場合は全体の範囲)
  const [numericRanges, setNumericRanges] = useState<NumericRangeFilters>(
    Object.keys(initialNumericRanges).length > 0 ? initialNumericRanges : numericRangesAll,
  );
  // 数値属性: 有効/無効 (初期値を反映)
  const [enabledRanges, setEnabledRanges] = useState<Record<string, boolean>>(initialEnabledRanges);
  // 空値含める (初期値を反映)
  const [includeEmptyValues, setIncludeEmptyValues] = useState<Record<string, boolean>>(initialIncludeEmptyValues);

  // --- ハンドラ ---
  const handleCheckboxChange = useCallback((attr: string, value: string) => {
    setCategoricalFilters((prev: AttributeFilters) => {
      const arr = prev[attr] ?? [];
      if (arr.includes(value)) {
        const filtered = arr.filter((v: string) => v !== value);
        const next = { ...prev };
        if (filtered.length === 0) delete next[attr];
        else next[attr] = filtered;
        return next;
      }
      return { ...prev, [attr]: [...arr, value] };
    });
  }, []);

  const handleRangeChange = useCallback(
    (attr: string, range: [number, number]) => {
      setNumericRanges((prev: NumericRangeFilters) => ({
        ...prev,
        [attr]: range,
      }));
    },
    []
  );

  const toggleRangeFilter = useCallback((attr: string, isEnabled: boolean) => {
    setEnabledRanges((prev: Record<string, boolean>) => ({ ...prev, [attr]: isEnabled }));
  }, []);

  const handleToggleIncludeEmpty = useCallback((attr: string, include: boolean) => {
    setIncludeEmptyValues((prev: Record<string, boolean>) => ({ ...prev, [attr]: include }));
  }, []);

  const handleClearFilters = useCallback(() => {
    setCategoricalFilters({});
    setNumericRanges(numericRangesAll);
    setEnabledRanges({});
    setIncludeEmptyValues({});
  }, [numericRangesAll]);

  // --- 適用 ---
  const onApply = useCallback(() => {
    onApplyFilters(categoricalFilters, numericRanges, includeEmptyValues, enabledRanges);
    onClose();
  }, [categoricalFilters, numericRanges, includeEmptyValues, enabledRanges, onApplyFilters, onClose]);

  // --- UI ---
  return (
    <DialogRoot lazyMount open={true} onOpenChange={onClose}>
      <DialogContent width="80vw" maxWidth="1200px">
        <DialogBody>
          <Box mb={6} mt={4}>
            <Heading as="h3" size="md" mb={2}>
              属性フィルター
            </Heading>
            <Text fontSize="sm" mb={5} color="gray.600">
              表示する意見グループを属性で絞り込みます。
            </Text>
            {attributeNames.length === 0 ? (
              <Text fontSize="sm" color="gray.500">
                利用できる属性情報がありません。CSVファイルをアップロードする際に、属性列を選択してください。
              </Text>
            ) : (
              attributeNames.map((attr) => {
                const values = availableAttributes[attr];
                const isNumeric = attributeTypes[attr] === "numeric";
                return (
                  <Box key={attr} mb={4}>
                    <Flex align="center" mb={2}>
                      <Heading size="sm" mb={0} mr={3}>
                        {attr}
                      </Heading>
                      {isNumeric && values.length > 0 && (
                        <Checkbox
                          isChecked={!!enabledRanges[attr]}
                          onChange={() => toggleRangeFilter(attr, !enabledRanges[attr])}
                        >
                          フィルター有効化
                        </Checkbox>
                      )}
                    </Flex>
                    {isNumeric && values.length > 0 ? (
                      <NumericRangeFilterItem
                        attr={attr}
                        range={numericRanges[attr] || numericRangesAll[attr]}
                        fullRange={numericRangesAll[attr]}
                        isEnabled={!!enabledRanges[attr]}
                        includeEmpty={!!includeEmptyValues[attr]}
                        onRangeChange={handleRangeChange}
                        onToggleEnabled={toggleRangeFilter}
                        onToggleIncludeEmpty={handleToggleIncludeEmpty}
                      />
                    ) : (
                      <Box pl={2}>
                        <Wrap style={{ gap: "8px" }}>
                          {values.map((value) => (
                            <WrapItem key={`${attr}-${value}`} mb={2} mr={3}>
                              <Box
                                p={1}
                                px={2}
                                borderWidth={1}
                                borderRadius="md"
                                bg={categoricalFilters[attr]?.includes(value) ? "blue.50" : "transparent"}
                                _hover={{ bg: "gray.50" }}
                                cursor="pointer"
                                onClick={() => handleCheckboxChange(attr, value)}
                              >
                                <Checkbox
                                  isChecked={categoricalFilters[attr]?.includes(value) || false}
                                  onChange={() => handleCheckboxChange(attr, value)}
                                >
                                  {value || "(空)"}
                                </Checkbox>
                                <Text as="span" fontSize="xs" ml={1} color="gray.500">
                                  {samples.filter((s) => s[attr] === value).length}
                                </Text>
                              </Box>
                            </WrapItem>
                          ))}
                        </Wrap>
                      </Box>
                    )}
                  </Box>
                );
              })
            )}
          </Box>
        </DialogBody>
        <DialogFooter justifyContent="space-between">
          <Button onClick={handleClearFilters} variant="outline" size="sm">
            すべてクリア
          </Button>
          <Button onClick={onApply} colorScheme="blue">
            設定を適用
          </Button>
        </DialogFooter>
      </DialogContent>
    </DialogRoot>
  );
}
