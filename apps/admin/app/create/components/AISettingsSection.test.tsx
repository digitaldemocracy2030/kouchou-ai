import { system } from "@/components/theme/system";
import { ChakraProvider } from "@chakra-ui/react";
import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useAISettings } from "../hooks/useAISettings";
import { AISettingsSection } from "./AISettingsSection";

jest.mock("@/components/ui/toaster", () => ({ toaster: { create: jest.fn() } }));

function Settings({ analysisModeLocked }: { analysisModeLocked?: boolean } = {}) {
  const ai = useAISettings();
  const noop = () => {};
  return (
    <ChakraProvider value={system}>
      <AISettingsSection
        provider={ai.provider}
        model={ai.model}
        workers={ai.workers}
        isPubcomMode={false}
        enableSourceLink={false}
        analysisMode={ai.analysisMode}
        onAnalysisModeChange={ai.handleAnalysisModeChange}
        analysisModeLocked={analysisModeLocked}
        onProviderChange={ai.handleProviderChange}
        onModelChange={ai.handleModelChange}
        onWorkersChange={noop}
        onIncreaseWorkers={noop}
        onDecreaseWorkers={noop}
        onPubcomModeChange={noop}
        onEnableSourceLinkChange={noop}
        getModelDescription={ai.getModelDescription}
        getProviderDescription={ai.getProviderDescription}
        getCurrentModels={ai.getCurrentModels}
        embeddingModel={ai.embeddingModel}
        onEmbeddingModelChange={ai.handleEmbeddingModelChange}
        getEmbeddingModelDescription={ai.getEmbeddingModelDescription}
        getCurrentEmbeddingModels={ai.getCurrentEmbeddingModels}
        isEmbeddingModelDisabled={ai.isEmbeddingModelDisabled}
        requiresConnectionSettings={ai.requiresConnectionSettings}
        isEmbeddedAtLocal={ai.isEmbeddedAtLocal}
        onEmbeddedAtLocalChange={noop}
        userApiKey=""
        onUserApiKeyChange={noop}
        promptSettings={{
          extraction: "",
          initialLabelling: "",
          mergeLabelling: "",
          overview: "",
          setExtraction: noop,
          setInitialLabelling: noop,
          setMergeLabelling: noop,
          setOverview: noop,
        }}
      />
    </ChakraProvider>
  );
}

const serverCatalog = require("../../../../api/src/services/model_catalog.json");
beforeEach(() => {
  window.localStorage.clear();
  global.fetch = jest.fn(async (url) => {
    const provider = new URL(String(url), "http://localhost").searchParams.get("provider");
    return {
      ok: true,
      json: async () =>
        provider === "azure"
          ? [{ value: "azure-server", label: "サーバー設定を使用" }]
          : serverCatalog.filter((row: { provider: string }) => row.provider === provider),
    } as Response;
  });
});

it("Azureの保存済みモデルを選択中のモデルとして表示しない", async () => {
  window.localStorage.setItem("kouchou_ai_provider", JSON.stringify("azure"));
  window.localStorage.setItem("kouchou_ai_model", JSON.stringify("gpt-4o"));
  render(<Settings />);

  const model = screen.getByRole("combobox", { name: "AIモデル" });
  await waitFor(() => expect(model).toBeDisabled());
  expect(model).toHaveDisplayValue("サーバー設定を使用");
  expect(screen.queryByRole("option", { name: "GPT-4o" })).not.toBeInTheDocument();
  expect(screen.getByText(/Azure OpenAIでは、サーバーに設定されたモデルを使用します/)).toBeInTheDocument();
  expect(screen.queryByText(/gpt-4o-miniと比較して高性能/)).not.toBeInTheDocument();
});

it("OpenAIからAzureへ切り替えると固定表示になり、戻すとモデルを選べる", async () => {
  const user = userEvent.setup();
  render(<Settings />);
  const provider = screen.getByRole("combobox", { name: "AIプロバイダー" });
  const model = screen.getByRole("combobox", { name: "AIモデル" });
  await screen.findByRole("option", { name: /GPT-4o（/ });
  await user.selectOptions(model, "gpt-4o");
  expect(model).toHaveValue("gpt-4o");
  await user.selectOptions(provider, "azure");
  await waitFor(() => expect(model).toBeDisabled());
  expect(model).toHaveDisplayValue("サーバー設定を使用");
  await user.selectOptions(provider, "openai");
  expect(model).toBeEnabled();
  await screen.findByRole("option", { name: /o3-mini/ });
  await user.selectOptions(model, "o3-mini");
  expect(model).toHaveValue("o3-mini");
  expect(screen.queryByText(/Azure OpenAIでは/)).not.toBeInTheDocument();
});

it("埋め込みモデルをチャットモデルとは別に選択でき、チャット一覧には混ざらない", async () => {
  render(<Settings />);
  const embedding = await screen.findByRole("combobox", { name: "埋め込みモデル" });
  expect(embedding).toBeEnabled();
  await within(embedding).findByRole("option", { name: "Text Embedding 3 Small" });
  // 埋め込みモデルはチャットモデルの一覧に出てこない
  const chat = screen.getByRole("combobox", { name: "AIモデル" });
  expect(within(chat).queryByRole("option", { name: "Text Embedding 3 Small" })).not.toBeInTheDocument();
});

it("LocalLLM選択時は埋め込みモデル選択が無効化される", async () => {
  const user = userEvent.setup();
  render(<Settings />);
  await user.selectOptions(screen.getByRole("combobox", { name: "AIプロバイダー" }), "local");
  const embedding = screen.getByRole("combobox", { name: "埋め込みモデル" });
  await waitFor(() => expect(embedding).toBeDisabled());
  expect(embedding).toHaveDisplayValue("サーバ内埋め込みを使用");
});

it("Geminiは従来どおりモデルを選択できる", async () => {
  const user = userEvent.setup();
  render(<Settings />);
  await user.selectOptions(screen.getByRole("combobox", { name: "AIプロバイダー" }), "gemini");
  const model = screen.getByRole("combobox", { name: "AIモデル" });
  expect(model).toBeEnabled();
  await screen.findByRole("option", { name: "Gemini 3.8 Flash（動作未確認）" });
  await user.selectOptions(model, "gemini-3.8-flash");
  expect(model).toHaveValue("gemini-3.8-flash");
});

it("分析方式を固定すると選択できず、引き継ぐ旨を表示する", async () => {
  render(<Settings analysisModeLocked />);
  const mode = screen.getByRole("combobox", { name: "分析方式" });
  expect(mode).toBeDisabled();
  expect(screen.getByText(/再利用元レポートの分析方式を引き継ぎます/)).toBeInTheDocument();
});

it("通常は分析方式を選択できる", async () => {
  render(<Settings />);
  expect(screen.getByRole("combobox", { name: "分析方式" })).toBeEnabled();
});
