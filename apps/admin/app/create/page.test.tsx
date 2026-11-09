import { system } from "@/components/theme/system";
import { toaster } from "@/components/ui/toaster";
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
let mockBodyLimitBytes = Number.POSITIVE_INFINITY;
jest.mock("@/app/utils/requestBodyLimit", () => ({
  ...jest.requireActual("@/app/utils/requestBodyLimit"),
  get SERVER_ACTION_BODY_SIZE_LIMIT_BYTES() {
    return mockBodyLimitBytes;
  },
}));

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
  mockBodyLimitBytes = Number.POSITIVE_INFINITY;
  jest.mocked(useAISettings).mockReturnValue({
    provider: "openai",
    model: "gpt-4o-mini",
    embeddingModel: "text-embedding-3-small",
    workers: 1,
    analysisMode: "hierarchical",
    userApiKey: "",
    selectedPrices: { chat: null, embedding: null },
    getCurrentModels: () => [],
    getCurrentEmbeddingModels: () => [],
    isEmbeddingModelDisabled: () => false,
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

// 本番では、スプレッドシート API とプラグインが属性列を attribute_<列名> の形で返す。
// 選択した列名に attribute_ を重ねて付けると、公開レポートの属性名が「attribute_地域」になる。
it.each([
  ["file", "attribute_地域"],
  ["spreadsheet", "attribute_地域"],
  ["plugin:source", "attribute_地域"],
  ["file", "地域"],
])("%s経路で属性列 %s を選ぶと、attribute_ を二重に付けずに送信する", async (inputType, attrCol) => {
  const row = { id: "1", answer: "意見", [attrCol]: "東京" };
  jest.mocked(useInputData).mockReturnValue({
    inputType,
    csv: new File(["csv"], "test.csv"),
    spreadsheetImported: true,
    spreadsheetData: [row],
    selectedCommentColumn: "answer",
    csvColumns: ["answer", attrCol],
    selectedAttributeColumns: [attrCol],
  } as unknown as ReturnType<typeof useInputData>);
  jest.mocked(usePluginData).mockReturnValue({
    plugins: [],
    pluginSelectedCommentColumn: "answer",
    pluginSelectedAttributeColumns: [attrCol],
    getPluginState: () => ({ imported: true, data: [row] }),
  } as unknown as ReturnType<typeof usePluginData>);
  const parseCsv = jest.requireMock("./parseCsv") as { parseCsv: () => Promise<unknown[]> };
  const originalParseCsv = parseCsv.parseCsv;
  parseCsv.parseCsv = async () => [row];
  jest.mocked(createReport).mockResolvedValue({ success: true } as Awaited<ReturnType<typeof createReport>>);
  try {
    render(
      <ChakraProvider value={system}>
        <Page />
      </ChakraProvider>,
    );
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: "作成前の確認へ" }));
    await user.click(await screen.findByRole("button", { name: "未確認のまま作成を開始" }));
    await waitFor(() => expect(createReport).toHaveBeenCalledTimes(1));
    const [{ comments }] = jest.mocked(createReport).mock.calls[0];
    expect(comments).toEqual([{ id: "1", comment: "意見", source: null, url: null, attribute_地域: "東京" }]);
  } finally {
    parseCsv.parseCsv = originalParseCsv;
  }
});

it("送信データが Server Action の本文上限を超えるときは、確認に進まず上限を案内する（s002）", async () => {
  jest.mocked(useInputData).mockReturnValue({
    inputType: "file",
    csv: new File(["csv"], "test.csv"),
    spreadsheetImported: false,
    spreadsheetData: [],
    selectedCommentColumn: "answer",
    csvColumns: ["answer", "age"],
    selectedAttributeColumns: ["age"],
  } as unknown as ReturnType<typeof useInputData>);
  // 本物の上限（100MB）の代わりに、このテストの送信データより小さい上限にする
  mockBodyLimitBytes = 64;
  render(
    <ChakraProvider value={system}>
      <Page />
    </ChakraProvider>,
  );
  const user = userEvent.setup();
  await user.click(screen.getByRole("button", { name: "作成前の確認へ" }));

  await waitFor(() =>
    expect(toaster.create).toHaveBeenCalledWith(
      expect.objectContaining({
        type: "error",
        title: "送信データが大きすぎます",
        description: expect.stringContaining("上限（約 100 MB）"),
      }),
    ),
  );
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  expect(createReport).not.toHaveBeenCalled();
});
