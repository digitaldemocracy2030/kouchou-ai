import { Checkbox } from "@/components/ui/checkbox";
import { Button, Field, HStack, Input, NativeSelect, Textarea, VStack } from "@chakra-ui/react";

/**
 * AI設定セクションコンポーネント
 */
export function AISettingsSection({
  provider,
  model,
  workers,
  isPubcomMode,
  enableSourceLink,
  onProviderChange,
  onModelChange,
  onWorkersChange,
  onIncreaseWorkers,
  onDecreaseWorkers,
  onPubcomModeChange,
  onEnableSourceLinkChange,
  getModelDescription,
  getProviderDescription,
  getCurrentModels,
  requiresConnectionSettings,
  isEmbeddedAtLocalDisabled,
  localLLMAddress,
  setLocalLLMAddress,
  promptSettings,
  isEmbeddedAtLocal,
  onEmbeddedAtLocalChange,
  fetchLocalLLMModels,
  userApiKey,
  onUserApiKeyChange,
}: {
  provider: string;
  model: string;
  workers: number;
  isPubcomMode: boolean;
  enableSourceLink: boolean;
  onProviderChange: (e: React.ChangeEvent<HTMLSelectElement>) => void;
  onModelChange: (e: React.ChangeEvent<HTMLSelectElement>) => void;
  onWorkersChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onIncreaseWorkers: () => void;
  onDecreaseWorkers: () => void;
  onPubcomModeChange: (checked: boolean | "indeterminate") => void;
  onEnableSourceLinkChange: (checked: boolean | "indeterminate") => void;
  getModelDescription: () => string;
  getProviderDescription: () => string;
  getCurrentModels: () => { value: string; label: string }[];
  requiresConnectionSettings: () => boolean;
  isEmbeddedAtLocalDisabled?: () => boolean;
  localLLMAddress?: string;
  setLocalLLMAddress?: (value: string) => void;
  fetchLocalLLMModels?: () => Promise<boolean>;
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
  userApiKey: string;
  onUserApiKeyChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
}) {
  const modelOptions = getCurrentModels();

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
        <Field.Label>AIプロバイダー</Field.Label>
        <NativeSelect.Root w={"40%"}>
          <NativeSelect.Field value={provider} onChange={onProviderChange}>
            <option value={"openai"}>OpenAI</option>
            <option value={"azure"}>Azure</option>
            <option value={"openrouter"}>OpenRouter</option>
            <option value={"local"}>LocalLLM</option>
          </NativeSelect.Field>
          <NativeSelect.Indicator />
        </NativeSelect.Root>
        <Field.HelperText>{getProviderDescription()}</Field.HelperText>
      </Field.Root>

      {/* TODO: azure の場合は別の方法が必要そうなので別途対応する */}
      {provider !== "local" && provider !== "azure" && (
        <Field.Root>
          <Field.Label>APIキー</Field.Label>
          <Input
            type="password"
            placeholder="独自のAPIキーを入力（空欄の場合はサーバー設定を使用）"
            value={userApiKey}
            onChange={onUserApiKeyChange}
          />
          <Field.HelperText>入力されたAPIキーを使用してレポートを生成できます。</Field.HelperText>
        </Field.Root>
      )}

      {requiresConnectionSettings() && (
        <Field.Root>
          <Field.Label>LocalLLM接続設定</Field.Label>
          <HStack>
            <Input
              placeholder="ollama:11434"
              value={localLLMAddress}
              onChange={(e) => setLocalLLMAddress?.(e.target.value)}
            />
            <Button
              onClick={async () => {
                if (fetchLocalLLMModels) {
                  await fetchLocalLLMModels();
                }
              }}
            >
              モデル取得
            </Button>
          </HStack>
          <Field.HelperText>
            OpenAI互換インターフェースで動作しているLLMサーバ（ollamaやLMStudio）のアドレスを指定してください。
            広聴AIのdockerでollamaサーバを起動している場合は ollama:11434で接続できます。
          </Field.HelperText>
        </Field.Root>
      )}

      <Field.Root>
        <Field.Label>並列実行数</Field.Label>
        <HStack>
          <Button onClick={onDecreaseWorkers} variant="outline">
            -
          </Button>
          <Input type="number" value={workers.toString()} min={1} max={100} onChange={onWorkersChange} />
          <Button onClick={onIncreaseWorkers} variant="outline">
            +
          </Button>
        </HStack>
        <Field.HelperText>
          LLM APIの並列実行数です。値を大きくすることでレポート出力が速くなりますが、
          APIプロバイダーのTierによってはレートリミットの上限に到達し、レポート出力が失敗する可能性があります。
        </Field.HelperText>
      </Field.Root>

      <Field.Root>
        <Field.Label>AIモデル</Field.Label>
        <NativeSelect.Root w={"40%"}>
          <NativeSelect.Field value={model} onChange={onModelChange}>
            {modelOptions.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </NativeSelect.Field>
          <NativeSelect.Indicator />
        </NativeSelect.Root>
        <Field.HelperText>{getModelDescription()}</Field.HelperText>
      </Field.Root>

      <Field.Root>
        <Checkbox
          checked={isEmbeddedAtLocal}
          onCheckedChange={(details) => {
            const { checked } = details;
            if (checked === "indeterminate") return;
            onEmbeddedAtLocalChange(checked);
          }}
          disabled={isEmbeddedAtLocalDisabled?.()}
        >
          埋め込み処理をサーバ内で行う
        </Checkbox>
        <Field.HelperText>
          埋め込み処理をサーバ内で行うことで、APIの利用料金を削減します。
          精度に関しては未検証であり、OpenAIを使った場合と大きく異なる結果になる可能性があります。
          {isEmbeddedAtLocalDisabled?.() && (
            <span style={{ color: "red" }}>
              ※ LocalLLMプロバイダーを選択している場合、この設定は強制的にONになります
            </span>
          )}
        </Field.HelperText>
      </Field.Root>

      <Field.Root>
        <Checkbox
          checked={enableSourceLink}
          onCheckedChange={(details) => {
            const { checked } = details;
            if (checked === "indeterminate") return;
            onEnableSourceLinkChange(checked);
          }}
        >
          ソースリンク機能を有効にする
        </Checkbox>
        <Field.HelperText>
          ONにした場合は、CSVのurlカラムの情報を使って、レポートの散布図上でデータ点をクリックすると元のソースにアクセスできます。
        </Field.HelperText>
      </Field.Root>

      <Field.Root>
        <Field.Label>抽出プロンプト</Field.Label>
        <Textarea
          h={"150px"}
          value={promptSettings.extraction}
          onChange={(e) => promptSettings.setExtraction(e.target.value)}
        />
        <Field.HelperText>AIに提示する抽出プロンプトです(通常は変更不要です)</Field.HelperText>
      </Field.Root>

      <Field.Root>
        <Field.Label>初期ラベリングプロンプト</Field.Label>
        <Textarea
          h={"150px"}
          value={promptSettings.initialLabelling}
          onChange={(e) => promptSettings.setInitialLabelling(e.target.value)}
        />
        <Field.HelperText>AIに提示する初期ラベリングプロンプトです(通常は変更不要です)</Field.HelperText>
      </Field.Root>

      <Field.Root>
        <Field.Label>統合ラベリングプロンプト</Field.Label>
        <Textarea
          h={"150px"}
          value={promptSettings.mergeLabelling}
          onChange={(e) => promptSettings.setMergeLabelling(e.target.value)}
        />
        <Field.HelperText>AIに提示する統合ラベリングプロンプトです(通常は変更不要です)</Field.HelperText>
      </Field.Root>

      <Field.Root>
        <Field.Label>要約プロンプト</Field.Label>
        <Textarea
          h={"150px"}
          value={promptSettings.overview}
          onChange={(e) => promptSettings.setOverview(e.target.value)}
        />
        <Field.HelperText>AIに提示する要約プロンプトです(通常は変更不要です)</Field.HelperText>
      </Field.Root>
    </VStack>
  );
}
