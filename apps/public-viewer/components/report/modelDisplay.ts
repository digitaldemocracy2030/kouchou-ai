import type { Config } from "@/type";

// サーバ内埋め込み（is_embedded_at_local）で使うモデル（analysis-core の request_to_local_embed）
export const LOCAL_EMBEDDING_MODEL = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2";

// Azure はチャット・埋め込みとも、config のモデル名ではなくサーバーに設定したデプロイを使う。
// config には管理画面の固定値（azure-server）や spec の既定値（text-embedding-3-small）が入るだけなので出さない。
export const AZURE_SERVER_MODEL_LABEL = "Azure OpenAI のサーバー設定";

// analysis-core の request_to_embed は、Gemini で OpenAI の名前や空が来ると gemini-embedding-001 に読み替える
const GEMINI_DEFAULT_EMBEDDING_MODEL = "gemini-embedding-001";
const OPENAI_EMBEDDING_ALIASES = new Set(["text-embedding-3-large", "text-embedding-3-small"]);

/** 分析手順に出す LLM のモデル名。`model` は各ステップの config に記録されたモデル名 */
export function chatModelDisplayName(
  config: Config,
  model: string,
  azureLabel: string = AZURE_SERVER_MODEL_LABEL,
): string {
  if (config.provider === "azure") return azureLabel;
  return model;
}

/** 分析手順に出す埋め込みモデル名（実際に埋め込みに使ったもの） */
export function embeddingModelDisplayName(config: Config, azureLabel: string = AZURE_SERVER_MODEL_LABEL): string {
  if (config.is_embedded_at_local) return LOCAL_EMBEDDING_MODEL;
  if (config.provider === "azure") return azureLabel;
  const model = config.embedding?.model ?? "";
  if (config.provider === "gemini" && (!model || OPENAI_EMBEDDING_ALIASES.has(model))) {
    return GEMINI_DEFAULT_EMBEDDING_MODEL;
  }
  return model;
}
