import { Box, Text, VStack } from "@chakra-ui/react";

/**
 * 属性カラム選択コンポーネント
 * このコンポーネントはCSVファイルから選択した属性カラムを管理します
 */
export function AttributeColumnsSelector({
  columns,
  selectedColumn,
  selectedAttributes,
  onAttributeChange,
}: {
  columns: string[];
  selectedColumn: string; // コメントカラム
  selectedAttributes: string[]; // 選択された属性カラム
  onAttributeChange: (attributes: string[]) => void; // 属性選択変更時のコールバック
}) {
  // 選択可能な属性カラム (コメントカラム、IDは除外)
  const availableAttributes = columns.filter((col) => col !== selectedColumn && col !== "id");

  // チェックボックスの変更ハンドラー
  const handleCheckboxChange = (attribute: string, isChecked: boolean) => {
    if (isChecked) {
      // 属性を追加
      onAttributeChange([...selectedAttributes, attribute]);
    } else {
      // 属性を削除
      onAttributeChange(selectedAttributes.filter((attr) => attr !== attribute));
    }
  };

  if (columns.length === 0) {
    return null;
  }

  return (
    <Box mt={4}>
      <Text fontWeight="bold" mb={1}>
        属性カラム選択
      </Text>
      <VStack align="flex-start" gap={2}>
        {availableAttributes.map((attribute) => (
          <Box key={attribute} display="flex" alignItems="center">
            <input
              type="checkbox"
              id={`attribute-${attribute}`}
              checked={selectedAttributes.includes(attribute)}
              onChange={(e) => handleCheckboxChange(attribute, e.target.checked)}
              style={{ marginRight: "8px" }}
            />
            <label htmlFor={`attribute-${attribute}`}>{attribute}</label>
          </Box>
        ))}
      </VStack>
      <Text fontSize="sm" color="gray.500" mt={1}>
        クロス分析に使用する属性カラムを選択してください。選択しない場合は意見のみの分析となります。
      </Text>
    </Box>
  );
}
