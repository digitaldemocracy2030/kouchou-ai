import { type ModelOption, modelDescription, useModelCatalog } from "./useModelCatalog";
export type { ModelOption } from "./useModelCatalog";
import { type ChangeEvent, useEffect, useState } from "react";

export type Provider = "openai" | "azure" | "openrouter" | "gemini" | "local";

const STORAGE_KEY_PREFIX = "kouchou_ai_";
const STORAGE_KEYS = {
  PROVIDER: `${STORAGE_KEY_PREFIX}provider`,
  MODEL: `${STORAGE_KEY_PREFIX}model`,
  WORKERS: `${STORAGE_KEY_PREFIX}workers`,
  LOCAL_LLM_ADDRESS: `${STORAGE_KEY_PREFIX}local_llm_address`,
  IS_EMBEDDED_AT_LOCAL: `${STORAGE_KEY_PREFIX}is_embedded_at_local`,
  ENABLE_SOURCE_LINK: `${STORAGE_KEY_PREFIX}enable_source_link`,
};

// LocalLLMのデフォルトアドレスを定数化
const DEFAULT_LOCAL_LLM_ADDRESS = process.env.NEXT_PUBLIC_LOCAL_LLM_ADDRESS || "ollama:11434";

// USE_AZUREがtrueの場合はAzure OpenAIをデフォルトにする
const DEFAULT_PROVIDER: Provider = process.env.NEXT_PUBLIC_USE_AZURE === "true" ? "azure" : "openai";

/**
 * LocalStorageから値を取得する関数
 * @param key ストレージキー
 * @param defaultValue デフォルト値
 */
function getFromStorage<T>(key: string, defaultValue: T): T {
  if (typeof window === "undefined") {
    return defaultValue;
  }

  try {
    const item = window.localStorage.getItem(key);
    return item ? JSON.parse(item) : defaultValue;
  } catch (error) {
    console.error(`LocalStorageからの読み込みに失敗しました: ${key}`, error);
    return defaultValue;
  }
}

/**
 * LocalStorageに値を保存する関数
 * @param key ストレージキー
 * @param value 保存する値
 */
function saveToStorage<T>(key: string, value: T): void {
  if (typeof window === "undefined") {
    return;
  }

  try {
    window.localStorage.setItem(key, JSON.stringify(value));
  } catch (error) {
    console.error(`LocalStorageへの保存に失敗しました: ${key}`, error);
  }
}

/**
 * AIモデル設定を管理するカスタムフック
 */
export function useAISettings() {
  const [provider, setProvider] = useState<Provider>(() =>
    getFromStorage<Provider>(STORAGE_KEYS.PROVIDER, DEFAULT_PROVIDER),
  );
  const [model, setModel] = useState<string>(() => getFromStorage<string>(STORAGE_KEYS.MODEL, ""));
  const [workers, setWorkers] = useState<number>(() => getFromStorage<number>(STORAGE_KEYS.WORKERS, 30));
  const [isPubcomMode, setIsPubcomMode] = useState<boolean>(true);
  const [isEmbeddedAtLocal, setIsEmbeddedAtLocal] = useState<boolean>(() =>
    getFromStorage<boolean>(STORAGE_KEYS.IS_EMBEDDED_AT_LOCAL, false),
  );
  const [enableSourceLink, setEnableSourceLink] = useState<boolean>(() =>
    getFromStorage<boolean>(STORAGE_KEYS.ENABLE_SOURCE_LINK, false),
  );

  const [localLLMAddress, setLocalLLMAddress] = useState<string>(() =>
    getFromStorage<string>(STORAGE_KEYS.LOCAL_LLM_ADDRESS, DEFAULT_LOCAL_LLM_ADDRESS),
  );

  const [userApiKey, setUserApiKey] = useState<string>("");

  const catalog = useModelCatalog(provider, provider === "local" ? localLLMAddress : undefined);
  useEffect(() => {
    if (provider === "local") setIsEmbeddedAtLocal(true);
  }, [provider]);
  useEffect(() => {
    // Empty means a new selection. Never overwrite restored/deprecated settings.
    if (!model && catalog.models.length) {
      setModel(catalog.models.find((candidate) => candidate.available !== false)?.value || "");
    }
  }, [catalog.models, model]);

  useEffect(() => {
    saveToStorage(STORAGE_KEYS.PROVIDER, provider);
  }, [provider]);

  useEffect(() => {
    saveToStorage(STORAGE_KEYS.MODEL, model);
  }, [model]);

  useEffect(() => {
    saveToStorage(STORAGE_KEYS.WORKERS, workers);
  }, [workers]);

  useEffect(() => {
    saveToStorage(STORAGE_KEYS.LOCAL_LLM_ADDRESS, localLLMAddress);
  }, [localLLMAddress]);

  useEffect(() => {
    saveToStorage(STORAGE_KEYS.IS_EMBEDDED_AT_LOCAL, isEmbeddedAtLocal);
  }, [isEmbeddedAtLocal]);

  useEffect(() => {
    saveToStorage(STORAGE_KEYS.ENABLE_SOURCE_LINK, enableSourceLink);
  }, [enableSourceLink]);

  const handleProviderChange = (e: ChangeEvent<HTMLSelectElement>) => {
    setProvider(e.target.value as Provider);
    setModel("");
  };

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
    setWorkers((prev: number) => Math.min(100, prev + 1));
  };

  /**
   * ワーカー数減少ハンドラー
   */
  const decreaseWorkers = () => {
    setWorkers((prev: number) => Math.max(1, prev - 1));
  };

  /**
   * モデル変更時のハンドラー
   */
  const handleModelChange = (e: ChangeEvent<HTMLSelectElement>) => {
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
   * ソースリンク設定変更時のハンドラー
   */
  const handleEnableSourceLinkChange = (checked: boolean | "indeterminate") => {
    if (checked === "indeterminate") return;
    setEnableSourceLink(checked);
  };

  /**
   * ユーザーAPIキー変更時のハンドラー
   */
  const handleUserApiKeyChange = (e: ChangeEvent<HTMLInputElement>) => {
    setUserApiKey(e.target.value);
  };

  /**
   * モデル説明文を取得
   */
  const selectedModel = catalog.models.find((option) => option.value === model);
  const modelError = catalog.loading
    ? "モデル一覧を取得中です。"
    : catalog.error ||
      (provider !== "azure" && (!selectedModel || selectedModel.available === false)
        ? "このモデルは利用できません。モデルを再選択してください。"
        : "");
  const getModelDescription = () => {
    if (provider === "azure")
      return `Azure OpenAIでは、サーバーに設定されたモデルを使用します。この画面では変更できません。${modelDescription(catalog.models[0])}`;
    return modelError || modelDescription(selectedModel);
  };
  const descriptions: Record<Provider, string> = {
    openai: "OpenAI APIを使用します。OpenAIのAPIキーが必要です。",
    azure: "Azure OpenAI Serviceを使用します。",
    openrouter: "OpenRouterを使用して複数のモデルにアクセスします。",
    gemini: "Google Gemini APIを使用します。GoogleのAPIキーが必要です。",
    local: "ローカルで実行されているLLMサーバーに接続します。",
  };
  const getProviderDescription = () => descriptions[provider];
  const getCurrentModels = (): ModelOption[] => {
    if (model && !catalog.models.some((option) => option.value === model)) {
      return [{ value: model, label: model, available: false }, ...catalog.models];
    }
    return catalog.models;
  };
  const fetchLocalLLMModels = async () => {
    catalog.reload();
    return true;
  };

  /**
   * LocalLLM接続設定が必要かどうか
   */
  const requiresConnectionSettings = () => {
    return provider === "local";
  };

  /**
   * 埋め込み処理をサーバ内で行うの設定が無効化されるべきかどうか
   * LocalLLMプロバイダーの場合は常にtrueで無効化される
   */
  const isEmbeddedAtLocalDisabled = () => {
    return provider === "local";
  };

  /**
   * AI設定をリセット
   */
  const resetAISettings = () => {
    setProvider(DEFAULT_PROVIDER);
    setModel("");
    setWorkers(30);
    setIsPubcomMode(true);
    setIsEmbeddedAtLocal(false);
    setEnableSourceLink(false);
    setLocalLLMAddress(DEFAULT_LOCAL_LLM_ADDRESS);
    setUserApiKey("");
    catalog.reload();

    saveToStorage(STORAGE_KEYS.PROVIDER, DEFAULT_PROVIDER);
    saveToStorage(STORAGE_KEYS.MODEL, "");
    saveToStorage(STORAGE_KEYS.WORKERS, 30);
    saveToStorage(STORAGE_KEYS.LOCAL_LLM_ADDRESS, DEFAULT_LOCAL_LLM_ADDRESS);
    saveToStorage(STORAGE_KEYS.IS_EMBEDDED_AT_LOCAL, false);
    saveToStorage(STORAGE_KEYS.ENABLE_SOURCE_LINK, false);
  };

  return {
    provider,
    model,
    modelError,
    reloadModels: catalog.reload,
    catalogWarning: catalog.models.find((option) => option.discovery_warning)?.discovery_warning,
    workers,
    isPubcomMode,
    isEmbeddedAtLocal,
    enableSourceLink,
    localLLMAddress,
    userApiKey,
    handleProviderChange,
    handleModelChange,
    handleWorkersChange,
    increaseWorkers,
    decreaseWorkers,
    handlePubcomModeChange,
    handleEnableSourceLinkChange,
    handleUserApiKeyChange,
    setLocalLLMAddress,
    getModelDescription,
    getProviderDescription,
    getCurrentModels,
    requiresConnectionSettings,
    isEmbeddedAtLocalDisabled,
    resetAISettings,
    setIsEmbeddedAtLocal,
    fetchLocalLLMModels,
  };
}
