import { type ModelOption, modelDescription, useModelCatalog } from "./useModelCatalog";
export type { ModelOption } from "./useModelCatalog";
import { type ChangeEvent, useEffect, useState } from "react";

export type Provider = "openai" | "azure" | "openrouter" | "gemini" | "local";

// 分析方式。"hierarchical"=埋め込みベースの階層クラスタリング（既定）、
// "llm_grouping"=LLM 直接グルーピング
export type AnalysisMode = "hierarchical" | "llm_grouping";

const STORAGE_KEY_PREFIX = "kouchou_ai_";
const STORAGE_KEYS = {
  PROVIDER: `${STORAGE_KEY_PREFIX}provider`,
  MODEL: `${STORAGE_KEY_PREFIX}model`,
  EMBEDDING_MODEL: `${STORAGE_KEY_PREFIX}embedding_model`,
  WORKERS: `${STORAGE_KEY_PREFIX}workers`,
  LOCAL_LLM_ADDRESS: `${STORAGE_KEY_PREFIX}local_llm_address`,
  IS_EMBEDDED_AT_LOCAL: `${STORAGE_KEY_PREFIX}is_embedded_at_local`,
  ENABLE_SOURCE_LINK: `${STORAGE_KEY_PREFIX}enable_source_link`,
  ANALYSIS_MODE: `${STORAGE_KEY_PREFIX}analysis_mode`,
};

const DEFAULT_ANALYSIS_MODE: AnalysisMode = "hierarchical";
/** 埋め込みモデルのカタログ行かどうか。kind 未指定はチャットモデル扱い。 */
const isEmbeddingRow = (option: ModelOption): boolean => (option.kind ?? "chat") === "embedding";

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
  const [embeddingModel, setEmbeddingModel] = useState<string>(() =>
    getFromStorage<string>(STORAGE_KEYS.EMBEDDING_MODEL, ""),
  );
  const [workers, setWorkers] = useState<number>(() => getFromStorage<number>(STORAGE_KEYS.WORKERS, 30));
  const [isPubcomMode, setIsPubcomMode] = useState<boolean>(true);
  const [isEmbeddedAtLocal, setIsEmbeddedAtLocal] = useState<boolean>(() =>
    getFromStorage<boolean>(STORAGE_KEYS.IS_EMBEDDED_AT_LOCAL, false),
  );
  const [enableSourceLink, setEnableSourceLink] = useState<boolean>(() =>
    getFromStorage<boolean>(STORAGE_KEYS.ENABLE_SOURCE_LINK, false),
  );
  // 元コメント本文の公開は入力データごとの判断なので、ブラウザには保存せず毎回 OFF から始める
  const [enableOriginalComments, setEnableOriginalComments] = useState<boolean>(false);
  const [analysisMode, setAnalysisMode] = useState<AnalysisMode>(() =>
    getFromStorage<AnalysisMode>(STORAGE_KEYS.ANALYSIS_MODE, DEFAULT_ANALYSIS_MODE),
  );

  const [localLLMAddress, setLocalLLMAddress] = useState<string>(() =>
    getFromStorage<string>(STORAGE_KEYS.LOCAL_LLM_ADDRESS, DEFAULT_LOCAL_LLM_ADDRESS),
  );

  const [userApiKey, setUserApiKey] = useState<string>("");

  const catalog = useModelCatalog(provider, provider === "local" ? localLLMAddress : undefined);
  // 1 回のカタログ取得にチャット・埋め込み両方のモデルが含まれるので、種別で振り分ける。
  const chatModels = catalog.models.filter((option) => !isEmbeddingRow(option));
  const embeddingModels = catalog.models.filter(isEmbeddingRow);
  // サーバ内埋め込み(ローカル)有効時と Azure(サーバー設定)では、埋め込みモデルの選択は使われない。
  const embeddingModelSelectionIgnored = isEmbeddedAtLocal || provider === "azure";

  useEffect(() => {
    if (provider === "local") setIsEmbeddedAtLocal(true);
  }, [provider]);
  useEffect(() => {
    // Empty means a new selection. Never overwrite restored/deprecated settings.
    if (!model && chatModels.length) {
      setModel(chatModels.find((candidate) => candidate.available !== false)?.value || "");
    }
  }, [chatModels, model]);
  useEffect(() => {
    // 埋め込みモデルも未選択なら利用可能な先頭を初期選択する。選択が使われない状況では触らない。
    if (embeddingModelSelectionIgnored) return;
    if (!embeddingModel && embeddingModels.length) {
      setEmbeddingModel(embeddingModels.find((candidate) => candidate.available !== false)?.value || "");
    }
  }, [embeddingModels, embeddingModel, embeddingModelSelectionIgnored]);

  useEffect(() => {
    saveToStorage(STORAGE_KEYS.PROVIDER, provider);
  }, [provider]);

  useEffect(() => {
    saveToStorage(STORAGE_KEYS.MODEL, model);
  }, [model]);

  useEffect(() => {
    saveToStorage(STORAGE_KEYS.EMBEDDING_MODEL, embeddingModel);
  }, [embeddingModel]);

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

  useEffect(() => {
    saveToStorage(STORAGE_KEYS.ANALYSIS_MODE, analysisMode);
  }, [analysisMode]);

  const handleAnalysisModeChange = (e: ChangeEvent<HTMLSelectElement>) => {
    setAnalysisMode(e.target.value as AnalysisMode);
  };

  const handleProviderChange = (e: ChangeEvent<HTMLSelectElement>) => {
    setProvider(e.target.value as Provider);
    setModel("");
    setEmbeddingModel("");
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
   * 埋め込みモデル変更時のハンドラー
   */
  const handleEmbeddingModelChange = (e: ChangeEvent<HTMLSelectElement>) => {
    setEmbeddingModel(e.target.value);
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
   * 元コメント公開設定変更時のハンドラー
   */
  const handleEnableOriginalCommentsChange = (checked: boolean | "indeterminate") => {
    if (checked === "indeterminate") return;
    setEnableOriginalComments(checked);
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
    if (model && !chatModels.some((option) => option.value === model)) {
      return [{ value: model, label: model, available: false }, ...chatModels];
    }
    return chatModels;
  };

  /**
   * 埋め込みモデルの選択がパイプラインで使われない状況かどうか。
   * - サーバ内埋め込み(ローカル)有効時: ローカルの埋め込みモデルが使われるため選択は無視される
   * - Azure: サーバー設定の埋め込みデプロイを使うため UI から変更できない
   */
  const isEmbeddingModelDisabled = () => embeddingModelSelectionIgnored;

  const selectedEmbeddingModel = embeddingModels.find((option) => option.value === embeddingModel);
  const embeddingModelError = embeddingModelSelectionIgnored
    ? ""
    : catalog.loading
      ? "モデル一覧を取得中です。"
      : catalog.error ||
        (embeddingModels.length === 0
          ? "このプロバイダーでは選択可能な埋め込みモデルがありません。サーバ内埋め込みをご利用ください。"
          : !selectedEmbeddingModel || selectedEmbeddingModel.available === false
            ? "この埋め込みモデルは利用できません。モデルを再選択してください。"
            : "");
  const getEmbeddingModelDescription = () => {
    if (provider === "azure")
      return "Azure OpenAIでは、サーバーに設定された埋め込みモデルを使用します。この画面では変更できません。";
    if (isEmbeddedAtLocal)
      return "サーバ内埋め込み（ローカルモデル）が有効なため、ここでの埋め込みモデル選択は使用されません。";
    return embeddingModelError || modelDescription(selectedEmbeddingModel);
  };
  const getCurrentEmbeddingModels = (): ModelOption[] => {
    if (embeddingModel && !embeddingModels.some((option) => option.value === embeddingModel)) {
      return [{ value: embeddingModel, label: embeddingModel, available: false }, ...embeddingModels];
    }
    return embeddingModels;
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
    setEmbeddingModel("");
    setWorkers(30);
    setIsPubcomMode(true);
    setIsEmbeddedAtLocal(false);
    setEnableSourceLink(false);
    setEnableOriginalComments(false);
    setAnalysisMode(DEFAULT_ANALYSIS_MODE);
    setLocalLLMAddress(DEFAULT_LOCAL_LLM_ADDRESS);
    setUserApiKey("");
    catalog.reload();

    saveToStorage(STORAGE_KEYS.PROVIDER, DEFAULT_PROVIDER);
    saveToStorage(STORAGE_KEYS.MODEL, "");
    saveToStorage(STORAGE_KEYS.EMBEDDING_MODEL, "");
    saveToStorage(STORAGE_KEYS.WORKERS, 30);
    saveToStorage(STORAGE_KEYS.LOCAL_LLM_ADDRESS, DEFAULT_LOCAL_LLM_ADDRESS);
    saveToStorage(STORAGE_KEYS.IS_EMBEDDED_AT_LOCAL, false);
    saveToStorage(STORAGE_KEYS.ENABLE_SOURCE_LINK, false);
    saveToStorage(STORAGE_KEYS.ANALYSIS_MODE, DEFAULT_ANALYSIS_MODE);
  };

  return {
    provider,
    model,
    embeddingModel,
    modelError,
    embeddingModelError,
    reloadModels: catalog.reload,
    catalogWarning: catalog.models.find((option) => option.discovery_warning)?.discovery_warning,
    workers,
    isPubcomMode,
    isEmbeddedAtLocal,
    enableSourceLink,
    enableOriginalComments,
    analysisMode,
    localLLMAddress,
    userApiKey,
    handleProviderChange,
    handleModelChange,
    handleAnalysisModeChange,
    handleEmbeddingModelChange,
    handleWorkersChange,
    increaseWorkers,
    decreaseWorkers,
    handlePubcomModeChange,
    handleEnableSourceLinkChange,
    handleEnableOriginalCommentsChange,
    handleUserApiKeyChange,
    setLocalLLMAddress,
    getModelDescription,
    getEmbeddingModelDescription,
    getProviderDescription,
    getCurrentModels,
    getCurrentEmbeddingModels,
    isEmbeddingModelDisabled,
    requiresConnectionSettings,
    isEmbeddedAtLocalDisabled,
    resetAISettings,
    setIsEmbeddedAtLocal,
    fetchLocalLLMModels,
  };
}
