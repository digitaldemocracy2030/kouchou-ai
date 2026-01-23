import { Field, NativeSelect } from "@chakra-ui/react";

// コメントカラム選択コンポーネント
export function CommentColumnSelector({
  columns,
  selectedColumn,
  onColumnChange,
}: {
  columns: string[];
  selectedColumn: string;
  onColumnChange: (column: string) => void;
}) {
  if (columns.length === 0) return null;

  return (
    <Field.Root mt={4}>
      <Field.Label>コメントカラム選択</Field.Label>
      <NativeSelect.Root w={"60%"}>
        <NativeSelect.Field value={selectedColumn} onChange={(e) => onColumnChange(e.target.value)}>
          <option value="">選択してください</option>
          {columns.map((col) => (
            <option key={col} value={col}>
              {col}
            </option>
          ))}
        </NativeSelect.Field>
        <NativeSelect.Indicator />
      </NativeSelect.Root>
      <Field.HelperText>
        分析対象のコメントが含まれるカラムを選んでください（それ以外のカラムは無視されます）。
      </Field.HelperText>
    </Field.Root>
  );
}
