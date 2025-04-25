import { Checkbox } from "@/components/ui/checkbox";
import {
    Button,
    Field,
    HStack,
    Input,
    NativeSelect,
    Textarea,
    VStack
} from "@chakra-ui/react";
import { usePromptSettings } from "../hooks/usePromptSettings";

/**
 * AI設定セクションコンポーネント
 */
export function AISettingsSection({
  model,
  workers,
  isPubcomMode,
  onModelChange,
  onWorkersChange,
  onIncreaseWorkers,
  onDecreaseWorkers,
  onPubcomModeChange,
  getModelDescription,
}: {
  model: string;
  workers: number;
  isPubcomMode: boolean;
  onModelChange: (e: React.ChangeEvent<HTMLSelectElement>) => void;
  onWorkersChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onIncreaseWorkers: () => void;
  onDecreaseWorkers: () => void;
  onPubcomModeChange: (checked: boolean | "indeterminate") => void;
  getModelDescription: () => string;
}) {
  // プロンプト設定のカスタムフック
  const promptSettings = usePromptSettings();

  return (
    <VStack gap={10}>
      <Field.Root>
        <Checkbox
          checked={isPubcomMode}
          onCheckedChange={(details) => {
            const { checked } = details;
            onPubcomModeChange(checked);
          }}
        >
          csv出力モード
        </Checkbox>
        <Field.HelperText>
          元のコメントと要約された意見をCSV形式で出力します。完成したCSVファイルはレポート一覧ページからダウンロードできます。
        </Field.HelperText>
      </Field.Root>

      <Field.Root>
        <Field.Label>並列実行数</Field.Label>
        <HStack>
          <Button
            onClick={onDecreaseWorkers}
            variant="outline"
          >
            -
          </Button>
          <Input
            type="number"
            value={workers.toString()}
            min={1}
            max={100}
            onChange={onWorkersChange}
          />
          <Button
            onClick={onIncreaseWorkers}
            variant="outline"
          >
            +
          </Button>
        </HStack>
        <Field.HelperText>
          OpenAI
          APIの並列実行数です。値を大きくすることでレポート出力が速くなりますが、OpenAIアカウントのTierによってはレートリミットの上限に到達し、レポート出力が失敗する可能性があります。
        </Field.HelperText>
      </Field.Root>

      <Field.Root>
        <Field.Label>AIモデル</Field.Label>
        <NativeSelect.Root w={"40%"}>
          <NativeSelect.Field
            value={model}
            onChange={onModelChange}
          >
            <option value={"gpt-4o-mini"}>OpenAI GPT-4o mini</option>
            <option value={"gpt-4o"}>OpenAI GPT-4o</option>
            <option value={"o3-mini"}>OpenAI o3-mini</option>
          </NativeSelect.Field>
          <NativeSelect.Indicator />
        </NativeSelect.Root>
        <Field.HelperText>
          {getModelDescription()}
        </Field.HelperText>
      </Field.Root>

      <Field.Root>
        <Field.Label>抽出プロンプト</Field.Label>
        <Textarea
          h={"150px"}
          value={promptSettings.extraction}
          onChange={(e) => promptSettings.setExtraction(e.target.value)}
        />
        <Field.HelperText>
          AIに提示する抽出プロンプトです(通常は変更不要です)
        </Field.HelperText>
      </Field.Root>

      <Field.Root>
        <Field.Label>初期ラベリングプロンプト</Field.Label>
        <Textarea
          h={"150px"}
          value={promptSettings.initial_labelling}
          onChange={(e) => promptSettings.setInitialLabelling(e.target.value)}
        />
        <Field.HelperText>
          AIに提示する初期ラベリングプロンプトです(通常は変更不要です)
        </Field.HelperText>
      </Field.Root>

      <Field.Root>
        <Field.Label>統合ラベリングプロンプト</Field.Label>
        <Textarea
          h={"150px"}
          value={promptSettings.merge_labelling}
          onChange={(e) => promptSettings.setMergeLabelling(e.target.value)}
        />
        <Field.HelperText>
          AIに提示する統合ラベリングプロンプトです(通常は変更不要です)
        </Field.HelperText>
      </Field.Root>

      <Field.Root>
        <Field.Label>要約プロンプト</Field.Label>
        <Textarea
          h={"150px"}
          value={promptSettings.overview}
          onChange={(e) => promptSettings.setOverview(e.target.value)}
        />
        <Field.HelperText>
          AIに提示する要約プロンプトです(通常は変更不要です)
        </Field.HelperText>
      </Field.Root>
    </VStack>
  );
}
