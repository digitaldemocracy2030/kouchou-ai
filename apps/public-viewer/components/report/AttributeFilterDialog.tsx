import { Checkbox } from "@/components/ui/checkbox";
import { DialogBody, DialogContent, DialogFooter, DialogRoot } from "@/components/ui/dialog";
import { Box, Button, Flex, Heading, Input, Text, Wrap, WrapItem } from "@chakra-ui/react";
import React, { useCallback, useMemo, useState } from "react";
import { FixedSizeList as List } from "react-window";

// リストアイテムのデータ型定義
type ListItemData = {
  attrName: string;
  values: string[];
  checkedList: string[];
  valueCounts: Record<string, number>;
  onChange: (attr: string, value: string) => void;
};

export type AttributeFilters = Record<string, string[]>;
type NumericRange = [number, number];
type NumericRangeFilters = Record<string, NumericRange>;
type AttributeTypes = Record<string, "numeric" | "categorical">;

export type AttributeMeta = {
  name: string;
  type: "numeric" | "categorical";
  values: string[];
  valueCounts: Record<string, number>;
  numericRange?: [number, number];
};

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
        {value || "(空)"}
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
  // 属性名リスト
  const attributeNames = useMemo(() => attributes.map((a) => a.name), [attributes]);

  // --- 編集用一時状態 ---
  const [editCategoricalFilters, setEditCategoricalFilters] = useState<AttributeFilters>(initialFilters);
  const [editNumericRanges, setEditNumericRanges] = useState<NumericRangeFilters>(
    Object.keys(initialNumericRanges).length > 0
      ? initialNumericRanges
      : Object.fromEntries(
          attributes
            .filter((a) => a.type === "numeric" && a.numericRange)
            .map((a) => [a.name, a.numericRange as NumericRange]),
        ),
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

  const handleRangeChange = useCallback(
    (attr: string, idx: 0 | 1, value: number) => {
      setEditNumericRanges((prev) => {
        const [min, max] = prev[attr] ?? attributes.find((a) => a.name === attr)?.numericRange ?? [0, 0];
        const next: NumericRange = idx === 0 ? [Math.min(value, max), max] : [min, Math.max(value, min)];
        return { ...prev, [attr]: next };
      });
    },
    [attributes],
  );

  const toggleRangeFilter = useCallback((attr: string) => {
    setEditEnabledRanges((prev) => ({ ...prev, [attr]: !prev[attr] }));
  }, []);

  const handleIncludeEmptyToggle = useCallback((attr: string) => {
    setEditIncludeEmptyValues((prev) => ({ ...prev, [attr]: !prev[attr] }));
  }, []);

  const handleClearFilters = useCallback(() => {
    setEditCategoricalFilters({});
    setEditNumericRanges(
      Object.fromEntries(
        attributes
          .filter((a) => a.type === "numeric" && a.numericRange)
          .map((a) => [a.name, a.numericRange as NumericRange]),
      ),
    );
    setEditEnabledRanges({});
    setEditIncludeEmptyValues({});
    setEditTextSearch("");
  }, [attributes]);

  // --- 適用 ---
  const onApply = useCallback(() => {
    onApplyFilters(
      editCategoricalFilters,
      editNumericRanges,
      editIncludeEmptyValues,
      editEnabledRanges,
      editTextSearch,
    );
    onClose();
  }, [
    editCategoricalFilters,
    editNumericRanges,
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
              フィルタ
            </Heading>
            <Text fontSize="sm" mb={5} color="gray.600">
              表示する意見グループを絞り込みます。フィルタ間はAND結合され、フィルタ内の条件はOR結合されます。
            </Text>

            <Box mb={6} borderWidth={1} borderRadius="md" p={3}>
              <Heading as="h4" size="sm" mb={2}>
                テキスト検索
              </Heading>
              <Input
                placeholder="検索したいテキストを入力してください。入力されたテキストが含まれる意見のみ表示されます。"
                value={editTextSearch}
                onChange={(e) => setEditTextSearch(e.target.value)}
                mb={2}
              />
            </Box>
            {attributes.length === 0 ? (
              <Text fontSize="sm" color="gray.500">
                利用できる属性情報がありません。CSVファイルをアップロードする際に、属性列を選択してください。
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
                          フィルター有効化
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
                            空の値を含める
                          </Checkbox>
                          <Text fontSize="xs" width="60px" textAlign="right" mr={2}>
                            最小: {attr.numericRange?.[0] ?? "-"}
                          </Text>
                          <Input
                            type="number"
                            value={editNumericRanges[attr.name]?.[0] ?? ""}
                            onChange={(e) => handleRangeChange(attr.name, 0, Number(e.target.value))}
                            size="sm"
                            width="100px"
                            disabled={!editEnabledRanges[attr.name]}
                          />
                          <Text mx={2}>～</Text>
                          <Input
                            type="number"
                            value={editNumericRanges[attr.name]?.[1] ?? ""}
                            onChange={(e) => handleRangeChange(attr.name, 1, Number(e.target.value))}
                            size="sm"
                            width="100px"
                            disabled={!editEnabledRanges[attr.name]}
                          />
                          <Text fontSize="xs" width="60px" textAlign="left" ml={2}>
                            最大: {attr.numericRange?.[1] ?? "-"}
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
