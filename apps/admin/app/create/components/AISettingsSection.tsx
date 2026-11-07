import { Checkbox } from "@/components/ui/checkbox";
import { Button, Field, HStack, Input, NativeSelect, Textarea, VStack } from "@chakra-ui/react";
import { type ModelOption, modelLabel } from "../hooks/useModelCatalog";

/**
 * AI設定セクションコンポーネント
 */
export function AISettingsSection({
  provider,
  model,
  workers,
  isPubcomMode,
  enableSourceLink,
  enableOriginalComments = false,
  analysisMode,
  onAnalysisModeChange,
  analysisModeLocked = false,
  onProviderChange,
  onModelChange,
  onWorkersChange,
  onIncreaseWorkers,
  onDecreaseWorkers,
  onPubcomModeChange,
  onEnableSourceLinkChange,
  onEnableOriginalCommentsChange,
  getModelDescription,
  getProviderDescription,
  getCurrentModels,
  embeddingModel,
  onEmbeddingModelChange,
  getEmbeddingModelDescription,
  getCurrentEmbeddingModels,
  isEmbeddingModelDisabled,
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
  /** 元コメント本文を公開レポートに含めるか（入力データの引用・再頒布が許されている場合だけ ON にする） */
  enableOriginalComments?: boolean;
  analysisMode: string;
  onAnalysisModeChange: (e: React.ChangeEvent<HTMLSelectElement>) => void;
  /** true のとき分析方式を変更不可にする（再利用時は元レポートの方式を引き継ぐため） */
  analysisModeLocked?: boolean;
  onProviderChange: (e: React.ChangeEvent<HTMLSelectElement>) => void;
  onModelChange: (e: React.ChangeEvent<HTMLSelectElement>) => void;
  onWorkersChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onIncreaseWorkers: () => void;
  onDecreaseWorkers: () => void;
  onPubcomModeChange: (checked: boolean | "indeterminate") => void;
  onEnableSourceLinkChange: (checked: boolean | "indeterminate") => void;
  onEnableOriginalCommentsChange?: (checked: boolean | "indeterminate") => void;
  getModelDescription: () => string;
  getProviderDescription: () => string;
  getCurrentModels: () => ModelOption[];
  embeddingModel?: string;
  onEmbeddingModelChange?: (e: React.ChangeEvent<HTMLSelectElement>) => void;
  getEmbeddingModelDescription?: () => string;
  getCurrentEmbeddingModels?: () => ModelOption[];
  isEmbeddingModelDisabled?: () => boolean;
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
  const isAzure = provider === "azure";
  const modelOptions = getCurrentModels();
  const showEmbeddingModelSelect = typeof getCurrentEmbeddingModels === "function";
  const embeddingModelOptions = showEmbeddingModelSelect ? (getCurrentEmbeddingModels?.() ?? []) : [];
  const embeddingDisabled = isEmbeddingModelDisabled?.() ?? false;
  const embeddingPlaceholder =
    isEmbeddedAtLocal && provider !== "azure" ? "サーバ内埋め込みを使用" : "サーバー設定を使用";

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

      <Field.Root disabled={analysisModeLocked}>
        <Field.Label>分析方式</Field.Label>
        <NativeSelect.Root w={"60%"}>
          <NativeSelect.Field value={analysisMode} onChange={onAnalysisModeChange}>
            <option value={"hierarchical"}>埋め込みベース（階層クラスタリング）</option>
            <option value={"llm_grouping"}>LLM直接グルーピング</option>
          </NativeSelect.Field>
          <NativeSelect.Indicator />
        </NativeSelect.Root>
        {analysisModeLocked && (
          <Field.HelperText>再利用元レポートの分析方式を引き継ぎます（再利用時は変更できません）。</Field.HelperText>
        )}
        <Field.HelperText>
          {analysisMode === "llm_grouping"
            ? "LLMがコメントから直接グループを発見し、各コメントをグループへ割り当てます（LLM直接グルーピング）。クラスタ数設定・初期/統合ラベリングプロンプトは使用されません。"
            : "埋め込みベクトルの階層クラスタリングでグループ化します（既定）。"}
        </Field.HelperText>
      </Field.Root>

      <Field.Root>
        <Field.Label>AIプロバイダー</Field.Label>
        <NativeSelect.Root w={"40%"}>
          <NativeSelect.Field value={provider} onChange={onProviderChange}>
            <option value={"openai"}>OpenAI</option>
            <option value={"azure"}>Azure</option>
            <option value={"openrouter"}>OpenRouter</option>
            <option value={"gemini"}>Gemini</option>
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
            LocalLLMを選択するとモデル一覧の自動取得を試みます。広聴AIのdockerでollamaサーバを起動している場合は
            ollama:11434で接続でき、失敗時はモデル取得ボタンで再試行できます。
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

      <Field.Root disabled={isAzure}>
        <Field.Label>AIモデル</Field.Label>
        <NativeSelect.Root w="full" maxW="600px">
          <NativeSelect.Field value={isAzure ? "" : model} onChange={onModelChange}>
            {isAzure ? (
              <option value="">サーバー設定を使用</option>
            ) : (
              modelOptions.map((option) => (
                <option key={option.value} value={option.value} disabled={option.available === false}>
                  {modelLabel(option)}
                </option>
              ))
            )}
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

      {showEmbeddingModelSelect && (
        <Field.Root disabled={embeddingDisabled}>
          <Field.Label>埋め込みモデル</Field.Label>
          <NativeSelect.Root w="full" maxW="600px">
            <NativeSelect.Field value={embeddingDisabled ? "" : embeddingModel} onChange={onEmbeddingModelChange}>
              {embeddingDisabled ? (
                <option value="">{embeddingPlaceholder}</option>
              ) : (
                embeddingModelOptions.map((option) => (
                  <option key={option.value} value={option.value} disabled={option.available === false}>
                    {modelLabel(option)}
                  </option>
                ))
              )}
            </NativeSelect.Field>
            <NativeSelect.Indicator />
          </NativeSelect.Root>
          <Field.HelperText>{getEmbeddingModelDescription?.()}</Field.HelperText>
        </Field.Root>
      )}

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
        <Checkbox
          checked={enableOriginalComments}
          onCheckedChange={(details) => {
            const { checked } = details;
            if (checked === "indeterminate") return;
            onEnableOriginalCommentsChange?.(checked);
          }}
        >
          元コメントの本文を公開レポートに含める
        </Checkbox>
        <Field.HelperText>
          ONにした場合は、意見の元になったコメントの本文がレポートのデータに含まれ、散布図や階層リストから確認できます。
          コメント本文はレポートを見られる人全員に公開されるので、入力データの引用・再頒布が許されている場合だけONにしてください。
          非公開にした属性値を持つコメントは含まれません。
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

      {/* 初期/統合ラベリングは hierarchical モード専用。LLM直接グルーピングでは使用しない。 */}
      {analysisMode !== "llm_grouping" && (
        <>
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
        </>
      )}

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
