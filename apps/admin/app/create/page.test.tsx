import { system } from "@/components/theme/system";
import { ChakraProvider } from "@chakra-ui/react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { createReport } from "./api/createReport";
import { useAISettings } from "./hooks/useAISettings";
import { useInputData } from "./hooks/useInputData";
import { usePluginData } from "./hooks/usePluginData";
import Page from "./page";

jest.mock("./api/createReport", () => ({ createReport: jest.fn() }));
jest.mock("next/navigation", () => ({ useRouter: () => ({ replace: jest.fn() }) }));
jest.mock("@/components/Header", () => ({ Header: () => null }));
jest.mock("@/components/ui/toaster", () => ({ toaster: { create: jest.fn() } }));
jest.mock("./hooks/useAISettings");
jest.mock("./hooks/useInputData");
jest.mock("./hooks/usePluginData");
jest.mock("./components/AISettingsSection", () => ({ AISettingsSection: () => null }));
jest.mock("./components/CsvFileTab", () => ({ CsvFileTab: () => null }));
jest.mock("./components/SpreadsheetTab", () => ({ SpreadsheetTab: () => null }));
jest.mock("./components/PluginTab", () => ({ PluginTab: () => null }));
jest.mock("./components/ClusterSettingsSection", () => ({ ClusterSettingsSection: () => null }));
jest.mock("./components/EnvironmentCheckDialog/verifyApiKey", () => ({ verifyApiKey: jest.fn() }));
jest.mock("./parseCsv", () => ({ parseCsv: async () => [{ id: "1", answer: "意見", age: "30" }] }));

const originalResizeObserver = global.ResizeObserver;
beforeAll(() => {
  global.ResizeObserver = jest
    .fn()
    .mockImplementation(() => ({ observe: jest.fn(), unobserve: jest.fn(), disconnect: jest.fn() }));
});
afterAll(() => {
  global.ResizeObserver = originalResizeObserver;
});

beforeEach(() => {
  jest.clearAllMocks();
  jest.mocked(useAISettings).mockReturnValue({
    provider: "openai",
    model: "gpt-4o-mini",
    workers: 1,
    userApiKey: "",
    getCurrentModels: () => [],
  } as unknown as ReturnType<typeof useAISettings>);
  jest.mocked(usePluginData).mockReturnValue({
    plugins: [],
    pluginSelectedCommentColumn: "answer",
    pluginSelectedAttributeColumns: ["age"],
    getPluginState: () => ({ imported: true, data: [{ id: "1", answer: "意見", age: "30" }] }),
  } as unknown as ReturnType<typeof usePluginData>);
});

it.each(["file", "spreadsheet", "plugin:source"])(
  "%s経路も確認前に送信せず、戻って修正した内容だけを一度送信する",
  async (inputType) => {
    jest.mocked(useInputData).mockReturnValue({
      inputType,
      csv: new File(["csv"], "test.csv"),
      spreadsheetImported: true,
      spreadsheetData: [{ id: "1", answer: "意見", age: "30" }],
      selectedCommentColumn: "answer",
      csvColumns: ["answer", "age"],
      selectedAttributeColumns: ["age"],
    } as unknown as ReturnType<typeof useInputData>);
    let resolve!: (result: Awaited<ReturnType<typeof createReport>>) => void;
    jest.mocked(createReport).mockReturnValue(
      new Promise((done) => {
        resolve = done;
      }),
    );
    render(
      <ChakraProvider value={system}>
        <Page />
      </ChakraProvider>,
    );
    const user = userEvent.setup();
    await user.type(screen.getByLabelText("タイトル（省略可）"), "変更前");
    await user.click(screen.getByRole("button", { name: "作成前の確認へ" }));
    expect(await screen.findByRole("dialog")).toBeVisible();
    expect(screen.getByText("コメント列：answer")).toBeVisible();
    expect(createReport).not.toHaveBeenCalled();
    await user.click(screen.getByRole("button", { name: "設定に戻る" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    await user.clear(screen.getByLabelText("タイトル（省略可）"));
    await user.type(screen.getByLabelText("タイトル（省略可）"), "変更後");
    await user.click(screen.getByRole("button", { name: "作成前の確認へ" }));
    const start = await screen.findByRole("button", { name: "未確認のまま作成を開始" });
    await user.dblClick(start);
    expect(createReport).toHaveBeenCalledTimes(1);
    expect(createReport).toHaveBeenCalledWith(
      expect.objectContaining({
        inputType,
        question: "変更後",
        comments: [expect.objectContaining({ id: "1", comment: "意見", attribute_age: "30" })],
      }),
    );
    resolve({ success: true });
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
  },
);
