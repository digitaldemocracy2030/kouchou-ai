import { Checkbox } from "@/components/ui/checkbox";
import { DialogBody, DialogContent, DialogFooter, DialogRoot } from "@/components/ui/dialog";
import { useMessages } from "@/lib/i18n/LanguageContext";
import { Box, Button, Flex, Heading, Input, Text, Wrap, WrapItem } from "@chakra-ui/react";
import React, { useCallback, useState } from "react";
import { FixedSizeList as List } from "react-window";
import type { AttributeFilters, AttributeMeta, NumericRangeFilters } from "./attributeFilterUtils";

// リストアイテムのデータ型定義
type ListItemData = {
  attrName: string;
  values: string[];
  checkedList: string[];
  valueCounts: Record<string, number>;
  onChange: (attr: string, value: string) => void;
};

type NumericRange = [number, number];
/** 入力中の数値範囲。途中の値（空欄・"-" など）も保てるよう文字列で持つ */
type NumericRangeInput = [string, string];

/** 数値属性ごとの全範囲（属性メタデータの最小・最大値） */
function defaultNumericRanges(attributes: AttributeMeta[]): NumericRangeFilters {
  return Object.fromEntries(
    attributes
      .filter((a) => a.type === "numeric" && a.numericRange)
      .map((a) => [a.name, a.numericRange as NumericRange]),
  );
}

function toRangeInputs(ranges: NumericRangeFilters): Record<string, NumericRangeInput> {
  return Object.fromEntries(Object.entries(ranges).map(([name, [min, max]]) => [name, [String(min), String(max)]]));
}

/**
 * 入力中の文字列を、適用する数値範囲に変換する。
 * 空欄や数値として読めない端は属性の全範囲の端とし、最小値が最大値より大きければ入れ替える。
 */
export function parseNumericRangeInputs(
  inputs: Record<string, NumericRangeInput>,
  attributes: AttributeMeta[],
): NumericRangeFilters {
  const defaults = defaultNumericRanges(attributes);
  const parse = (text: string, fallback: number) => {
    const trimmed = text.trim();
    if (trimmed === "") return fallback;
    const n = Number(trimmed);
    return Number.isFinite(n) ? n : fallback;
  };
  const result: NumericRangeFilters = {};
  for (const [name, [minText, maxText]] of Object.entries(inputs)) {
    const [defaultMin, defaultMax] = defaults[name] ?? [Number.NEGATIVE_INFINITY, Number.POSITIVE_INFINITY];
    const min = parse(minText, defaultMin);
    const max = parse(maxText, defaultMax);
    result[name] = min <= max ? [min, max] : [max, min];
  }
  return result;
}

type AttributeFilterDialogProps = {
  attributes: AttributeMeta[];
  initialFilters?: AttributeFilters;
  initialNumericRanges?: NumericRangeFilters;
  initialEnabledRanges?: Record<string, boolean>;
  initialIncludeEmptyValues?: Record<string, boolean>;
  initialTextSearch?: string;
  onApplyFilters: (
    filters: AttributeFilters,
    numericRanges: NumericRangeFilters,
    includeEmpty: Record<string, boolean>,
    enabledRanges: Record<string, boolean>,
    textSearch: string,
  ) => void;
  onClose: () => void;
};

// 値ごとのチェックボックスをメモ化
const ValueCheckbox = React.memo(function ValueCheckbox({
  attrName,
  value,
  checked,
  count,
  onChange,
}: {
  attrName: string;
  value: string;
  checked: boolean;
  count: number;
  onChange: (attr: string, value: string) => void;
}) {
  const messages = useMessages();
  return (
    <Box
      p={1}
      px={2}
      borderWidth={1}
      borderRadius="md"
      bg={checked ? "blue.50" : "transparent"}
      _hover={{ bg: "gray.50" }}
      cursor="pointer"
      onClick={() => onChange(attrName, value)}
    >
      <Checkbox checked={checked} onChange={() => onChange(attrName, value)}>
        {value || messages.empty}
      </Checkbox>
      <Text as="span" fontSize="xs" ml={1} color="gray.500">
        {count}
      </Text>
    </Box>
  );
});

export function AttributeFilterDialog({
  attributes = [], // デフォルト空配列でTypeError防止
  onClose,
  onApplyFilters,
  initialFilters = {},
  initialNumericRanges = {},
  initialEnabledRanges = {},
  initialIncludeEmptyValues = {},
  initialTextSearch = "",
}: AttributeFilterDialogProps) {
  const messages = useMessages();
  // --- 編集用一時状態 ---
  const [editCategoricalFilters, setEditCategoricalFilters] = useState<AttributeFilters>(initialFilters);
  // 入力中は文字列のまま保持し、数値への変換・入れ替えは適用時に行う
  // （入力のたびに丸めると、1 文字目で最小値・最大値に置き換わり桁が崩れる）
  const [editRangeInputs, setEditRangeInputs] = useState<Record<string, NumericRangeInput>>(() =>
    toRangeInputs({ ...defaultNumericRanges(attributes), ...initialNumericRanges }),
  );
  const [editEnabledRanges, setEditEnabledRanges] = useState<Record<string, boolean>>(initialEnabledRanges);
  const [editIncludeEmptyValues, setEditIncludeEmptyValues] =
    useState<Record<string, boolean>>(initialIncludeEmptyValues);
  const [editTextSearch, setEditTextSearch] = useState<string>(initialTextSearch);

  // --- ハンドラ ---
  const handleCheckboxChange = useCallback((attr: string, value: string) => {
    setEditCategoricalFilters((prev) => {
      // React 18: setStateバッチ化で高速化
      const arr = prev[attr] ?? [];
      const nextArr = arr.includes(value) ? arr.filter((v) => v !== value) : [...arr, value];
      const next = { ...prev };
      if (nextArr.length === 0) delete next[attr];
      else next[attr] = nextArr;
      return next;
    });
  }, []);

  const handleRangeChange = useCallback((attr: string, idx: 0 | 1, value: string) => {
    setEditRangeInputs((prev) => {
      const next: NumericRangeInput = [...(prev[attr] ?? ["", ""])];
      next[idx] = value;
      return { ...prev, [attr]: next };
    });
  }, []);

  const toggleRangeFilter = useCallback((attr: string) => {
    setEditEnabledRanges((prev) => ({ ...prev, [attr]: !prev[attr] }));
  }, []);

  const handleIncludeEmptyToggle = useCallback((attr: string) => {
    setEditIncludeEmptyValues((prev) => ({ ...prev, [attr]: !prev[attr] }));
  }, []);

  const handleClearFilters = useCallback(() => {
    setEditCategoricalFilters({});
    setEditRangeInputs(toRangeInputs(defaultNumericRanges(attributes)));
    setEditEnabledRanges({});
    setEditIncludeEmptyValues({});
    setEditTextSearch("");
  }, [attributes]);

  // --- 適用 ---
  const onApply = useCallback(() => {
    onApplyFilters(
      editCategoricalFilters,
      parseNumericRangeInputs(editRangeInputs, attributes),
      editIncludeEmptyValues,
      editEnabledRanges,
      editTextSearch,
    );
    onClose();
  }, [
    editCategoricalFilters,
    editRangeInputs,
    attributes,
    editIncludeEmptyValues,
    editEnabledRanges,
    editTextSearch,
    onApplyFilters,
    onClose,
  ]);

  // --- UI ---
  return (
    <DialogRoot lazyMount open onOpenChange={onClose}>
      <DialogContent width="80vw" maxWidth="1200px">
        <DialogBody>
          <Box mb={6} mt={4}>
            <Heading as="h3" size="md" mb={2}>
              {messages.filter}
            </Heading>
            <Text fontSize="sm" mb={5} color="gray.600">
              {messages.filterDescription}
            </Text>

            <Box mb={6} borderWidth={1} borderRadius="md" p={3}>
              <Heading as="h4" size="sm" mb={2}>
                {messages.textSearch}
              </Heading>
              <Input
                placeholder={messages.textSearchPlaceholder}
                value={editTextSearch}
                onChange={(e) => setEditTextSearch(e.target.value)}
                mb={2}
              />
            </Box>
            {attributes.length === 0 ? (
              <Text fontSize="sm" color="gray.500">
                {messages.noAttributes}
              </Text>
            ) : (
              attributes.map((attr) => {
                const isNumeric = attr.type === "numeric";
                return (
                  <Box key={attr.name} mb={4}>
                    <Flex align="center" mb={2}>
                      <Heading size="sm" mb={0} mr={3}>
                        {attr.name}
                      </Heading>
                      {isNumeric && attr.values.length > 0 && (
                        <Checkbox
                          checked={!!editEnabledRanges[attr.name]}
                          onChange={() => toggleRangeFilter(attr.name)}
                        >
                          {messages.enableRange}
                        </Checkbox>
                      )}
                    </Flex>
                    {isNumeric && attr.values.length > 0 ? (
                      <Box pl={2} pr={4} borderWidth={1} borderRadius="md" p={2}>
                        <Flex align="center">
                          <Checkbox
                            checked={!!editIncludeEmptyValues[attr.name]}
                            onChange={() => handleIncludeEmptyToggle(attr.name)}
                            disabled={!editEnabledRanges[attr.name]}
                            mr={4}
                          >
                            {messages.includeEmpty}
                          </Checkbox>
                          <Text fontSize="xs" width="60px" textAlign="right" mr={2}>
                            {messages.min}: {attr.numericRange?.[0] ?? "-"}
                          </Text>
                          <Input
                            type="number"
                            value={editRangeInputs[attr.name]?.[0] ?? ""}
                            onChange={(e) => handleRangeChange(attr.name, 0, e.target.value)}
                            size="sm"
                            width="100px"
                            disabled={!editEnabledRanges[attr.name]}
                          />
                          <Text mx={2}>～</Text>
                          <Input
                            type="number"
                            value={editRangeInputs[attr.name]?.[1] ?? ""}
                            onChange={(e) => handleRangeChange(attr.name, 1, e.target.value)}
                            size="sm"
                            width="100px"
                            disabled={!editEnabledRanges[attr.name]}
                          />
                          <Text fontSize="xs" width="60px" textAlign="left" ml={2}>
                            {messages.max}: {attr.numericRange?.[1] ?? "-"}
                          </Text>
                        </Flex>
                      </Box>
                    ) : (
                      <Box pl={2}>
                        {attr.values.length > 100 ? (
                          <List
                            height={300}
                            itemCount={attr.values.length}
                            itemSize={40}
                            width={"100%"}
                            itemData={{
                              attrName: attr.name,
                              values: attr.values,
                              checkedList: editCategoricalFilters[attr.name] ?? [],
                              valueCounts: attr.valueCounts,
                              onChange: handleCheckboxChange,
                            }}
                          >
                            {({
                              index,
                              style,
                              data,
                            }: { index: number; style: React.CSSProperties; data: ListItemData }) => {
                              const value = data.values[index];
                              return (
                                <div style={style} key={`${data.attrName}-${value}`}>
                                  <ValueCheckbox
                                    attrName={data.attrName}
                                    value={value}
                                    checked={data.checkedList.includes(value)}
                                    count={data.valueCounts[value] ?? 0}
                                    onChange={data.onChange}
                                  />
                                </div>
                              );
                            }}
                          </List>
                        ) : (
                          <Wrap style={{ gap: "8px" }}>
                            {attr.values.map((value) => (
                              <WrapItem key={`${attr.name}-${value}`} mb={2} mr={3}>
                                <ValueCheckbox
                                  attrName={attr.name}
                                  value={value}
                                  checked={editCategoricalFilters[attr.name]?.includes(value) || false}
                                  count={attr.valueCounts[value] ?? 0}
                                  onChange={handleCheckboxChange}
                                />
                              </WrapItem>
                            ))}
                          </Wrap>
                        )}
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
            {messages.clearAll}
          </Button>
          <Button onClick={onApply} colorScheme="blue">
            {messages.apply}
          </Button>
        </DialogFooter>
      </DialogContent>
    </DialogRoot>
  );
}
