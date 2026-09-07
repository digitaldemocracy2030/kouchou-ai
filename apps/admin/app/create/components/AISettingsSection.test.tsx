import { system } from "@/components/theme/system";
import { ChakraProvider } from "@chakra-ui/react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { useAISettings } from "../hooks/useAISettings";
import { AISettingsSection } from "./AISettingsSection";

jest.mock("@/components/ui/toaster", () => ({ toaster: { create: jest.fn() } }));

function Settings() {
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

beforeEach(() => window.localStorage.clear());

it("Azureの保存済みモデルを選択中のモデルとして表示しない", () => {
  window.localStorage.setItem("kouchou_ai_provider", JSON.stringify("azure"));
  window.localStorage.setItem("kouchou_ai_model", JSON.stringify("gpt-4o"));
  render(<Settings />);

  const model = screen.getByRole("combobox", { name: "AIモデル" });
  expect(model).toBeDisabled();
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
  await user.selectOptions(model, "gpt-4o");
  expect(model).toHaveValue("gpt-4o");
  await user.selectOptions(provider, "azure");
  expect(model).toBeDisabled();
  expect(model).toHaveDisplayValue("サーバー設定を使用");
  await user.selectOptions(provider, "openai");
  expect(model).toBeEnabled();
  await user.selectOptions(model, "o3-mini");
  expect(model).toHaveValue("o3-mini");
  expect(screen.queryByText(/Azure OpenAIでは/)).not.toBeInTheDocument();
});

it("Geminiは従来どおりモデルを選択できる", async () => {
  const user = userEvent.setup();
  render(<Settings />);
  await user.selectOptions(screen.getByRole("combobox", { name: "AIプロバイダー" }), "gemini");
  const model = screen.getByRole("combobox", { name: "AIモデル" });
  expect(model).toBeEnabled();
  await user.selectOptions(model, "gemini-1.5-pro");
  expect(model).toHaveValue("gemini-1.5-pro");
});
