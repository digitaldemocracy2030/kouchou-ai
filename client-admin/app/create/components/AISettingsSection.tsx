import React from "react";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Button,
  Field,
  HStack,
  Input,
  NativeSelect,
  Textarea,
  VStack,
  Text,
  Spinner
} from "@chakra-ui/react";
import { LLMProvider } from "../hooks/useAISettings";

/**
 * AI設定セクションコンポーネント
 */
export function AISettingsSection({
  provider,
  model,
  workers,
  isPubcomMode,
  availableModels,
  isVerifyingProvider,
  providerError,
  onProviderChange,
  onModelChange,
  onWorkersChange,
  onIncreaseWorkers,
  onDecreaseWorkers,
  onPubcomModeChange,
  onVerifyProvider,
  getModelDescription,
  promptSettings,
  isEmbeddedAtLocal,
  onEmbeddedAtLocalChange,
}: {
  provider: LLMProvider;
  model: string;
  workers: number;
  isPubcomMode: boolean;
  availableModels: string[];
  isVerifyingProvider: boolean;
  providerError: string | null;
  onProviderChange: (e: React.ChangeEvent<HTMLSelectElement>) => void;
  onModelChange: (e: React.ChangeEvent<HTMLSelectElement>) => void;
  onWorkersChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onIncreaseWorkers: () => void;
  onDecreaseWorkers: () => void;
  onPubcomModeChange: (checked: boolean | "indeterminate") => void;
  onVerifyProvider: () => void;
  getModelDescription: () => string;
  promptSettings: {
    extraction: string;
    initialLabelling: string;
    mergeLabelling: string;
    overview: string;
    setExtraction: (value: string) => void;
    setInitialLabelling: (value: string) => void;
    setMergeLabelling: (value: string) => void;
    setOverview: (value: string) => void;
  };
  isEmbeddedAtLocal: boolean;
  onEmbeddedAtLocalChange: (checked: boolean | "indeterminate") => void;
}) {

  return (
    <VStack gap={10}>
      <Field.Root>
        <Checkbox
          checked={isPubcomMode}
          onCheckedChange={(details: { checked: boolean | "indeterminate" }) => {
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
          LLM APIの並列実行数です。値を大きくすることでレポート出力が速くなりますが、APIプロバイダーのTierによってはレートリミットの上限に到達し、レポート出力が失敗する可能性があります。
        </Field.HelperText>
      </Field.Root>

      <Field.Root>
        <Field.Label>LLMプロバイダー</Field.Label>
        <HStack>
          <NativeSelect.Root w={"40%"}>
            <NativeSelect.Field
              value={provider}
              onChange={onProviderChange}
            >
              <option value={"openai"}>OpenAI</option>
              <option value={"azure"}>Azure OpenAI</option>
              <option value={"openrouter"}>Open Router</option>
              <option value={"localllm"}>LocalLLM (LM Studio/ollama)</option>
            </NativeSelect.Field>
            <NativeSelect.Indicator />
          </NativeSelect.Root>
          <Button
            onClick={onVerifyProvider}
            isLoading={isVerifyingProvider}
            loadingText="検証中"
            variant="outline"
          >
            接続検証
          </Button>
        </HStack>
        {providerError && (
          <Text color="red.500" fontSize="sm" mt={1}>
            エラー: {providerError}
          </Text>
        )}
        <Field.HelperText>
          使用するLLMプロバイダーを選択し、「接続検証」ボタンをクリックして利用可能なモデルを取得してください。
        </Field.HelperText>
      </Field.Root>

      <Field.Root>
        <Field.Label>AIモデル</Field.Label>
        <NativeSelect.Root w={"40%"}>
          <NativeSelect.Field
            value={model}
            onChange={onModelChange}
          >
            {availableModels.length > 0 ? (
              availableModels.map((modelName) => (
                <option key={modelName} value={modelName}>
                  {modelName}
                </option>
              ))
            ) : provider === "openai" ? (
              <>
                <option value={"gpt-4o-mini"}>OpenAI GPT-4o mini</option>
                <option value={"gpt-4o"}>OpenAI GPT-4o</option>
                <option value={"o3-mini"}>OpenAI o3-mini</option>
              </>
            ) : (
              <option value={model}>{model}</option>
            )}
          </NativeSelect.Field>
          <NativeSelect.Indicator />
        </NativeSelect.Root>
        {isVerifyingProvider && <Spinner size="sm" ml={2} />}
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
          value={promptSettings.initialLabelling}
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
          value={promptSettings.mergeLabelling}
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
      <Field.Root>
        <Checkbox
          checked={isEmbeddedAtLocal}
          onCheckedChange={(details) => {
            const { checked } = details;
            if (checked === "indeterminate") return;
            onEmbeddedAtLocalChange(checked);
          }}
        >
          埋め込み処理をサーバ内で行う
        </Checkbox>
        <Field.HelperText>
          埋め込み処理をサーバ内で行うことで、APIの利用料金を削減します。
          精度に関しては未検証であり、OpenAIを使った場合と大きく異なる結果になる可能性があります。
        </Field.HelperText>
      </Field.Root>
    </VStack>
  );
}
