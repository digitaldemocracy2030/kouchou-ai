import { useState } from "react";

export type LLMProvider = "openai" | "azure" | "openrouter" | "localllm";

const DEFAULT_MODELS: Record<LLMProvider, string> = {
  openai: "gpt-4o-mini",
  azure: "gpt-4o",
  openrouter: "openai/gpt-4o",
  localllm: "local-model",
};

/**
 * AIモデル設定を管理するカスタムフック
 */
export function useAISettings() {
  // AIモデル関連の状態
  const [provider, setProvider] = useState<LLMProvider>("openai");
  const [model, setModel] = useState<string>(DEFAULT_MODELS.openai);
  const [workers, setWorkers] = useState<number>(30);
  const [isPubcomMode, setIsPubcomMode] = useState<boolean>(true);
  const [isEmbeddedAtLocal, setIsEmbeddedAtLocal] = useState<boolean>(false);
  const [availableModels, setAvailableModels] = useState<string[]>([]);
  const [isVerifyingProvider, setIsVerifyingProvider] = useState<boolean>(false);
  const [providerError, setProviderError] = useState<string | null>(null);

  /**
   * ワーカー数変更時のハンドラー
   */
  const handleWorkersChange = (value: number) => {
    setWorkers(Math.max(1, Math.min(100, value)));
  };

  /**
   * ワーカー数増加ハンドラー
   */
  const increaseWorkers = () => {
    setWorkers((prev) => Math.min(100, prev + 1));
  };

  /**
   * ワーカー数減少ハンドラー
   */
  const decreaseWorkers = () => {
    setWorkers((prev) => Math.max(1, prev - 1));
  };

  /**
   * プロバイダー変更時のハンドラー
   */
  const handleProviderChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const newProvider = e.target.value as LLMProvider;
    setProvider(newProvider);
    setModel(DEFAULT_MODELS[newProvider]);
    setProviderError(null);
  };

  /**
   * モデル変更時のハンドラー
   */
  const handleModelChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    setModel(e.target.value);
  };

  /**
   * パブコムモード変更時のハンドラー
   */
  const handlePubcomModeChange = (checked: boolean | "indeterminate") => {
    if (checked === "indeterminate") return;
    setIsPubcomMode(checked);
  };

  /**
   * プロバイダーの接続を検証し、利用可能なモデルを取得
   */
  const verifyProvider = async () => {
    setIsVerifyingProvider(true);
    setProviderError(null);
    
    try {
      const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASEPATH}/admin/environment/verify-llm-provider?provider=${provider}`, {
        headers: {
          "x-api-key": process.env.NEXT_PUBLIC_ADMIN_API_KEY || "",
        },
      });
      
      const data = await response.json();
      
      if (data.success) {
        setAvailableModels(data.supported_models);
        if (data.supported_models.length > 0) {
          setModel(data.supported_models[0]);
        }
      } else {
        setProviderError(data.message);
        setAvailableModels([]);
      }
    } catch (error) {
      setProviderError("プロバイダーの検証中にエラーが発生しました");
      setAvailableModels([]);
    } finally {
      setIsVerifyingProvider(false);
    }
  };

  /**
   * モデル説明文を取得
   */
  const getModelDescription = () => {
    if (provider === "openai") {
      if (model === "gpt-4o-mini") {
        return "GPT-4o mini：最も安価に利用できるモデルです。価格の詳細はOpenAIが公開しているAPI料金のページをご参照ください。";
      } else if (model === "gpt-4o") {
        return "GPT-4o：gpt-4o-miniと比較して高性能なモデルです。性能は高くなりますが、gpt-4o-miniと比較してOpenAI APIの料金は高くなります。";
      } else if (model === "o3-mini") {
        return "o3-mini：gpt-4oよりも高度な推論能力を備えたモデルです。性能はより高くなりますが、gpt-4oと比較してOpenAI APIの料金は高くなります。";
      }
    } else if (provider === "openrouter") {
      return "Open Router：複数のAIプロバイダーのモデルに統一されたAPIでアクセスできるサービスです。";
    } else if (provider === "localllm") {
      return "LocalLLM：LM StudioやollamaなどのローカルLLMをOpenAI互換APIで利用できます。";
    } else if (provider === "azure") {
      return "Azure OpenAI：MicrosoftのAzure上で提供されるOpenAIのモデルです。";
    }
    return "";
  };

  /**
   * AI設定をリセット
   */
  const resetAISettings = () => {
    setProvider("openai");
    setModel(DEFAULT_MODELS.openai);
    setWorkers(30);
    setIsPubcomMode(true);
    setIsEmbeddedAtLocal(false);
    setAvailableModels([]);
    setProviderError(null);
  };

  return {
    provider,
    model,
    workers,
    isPubcomMode,
    isEmbeddedAtLocal,
    availableModels,
    isVerifyingProvider,
    providerError,
    handleProviderChange,
    handleModelChange,
    handleWorkersChange,
    increaseWorkers,
    decreaseWorkers,
    handlePubcomModeChange,
    verifyProvider,
    getModelDescription,
    resetAISettings,
    setIsEmbeddedAtLocal,
  };
}
