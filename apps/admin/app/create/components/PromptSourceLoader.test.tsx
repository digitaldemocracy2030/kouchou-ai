import { system } from "@/components/theme/system";
import { ChakraProvider, Textarea } from "@chakra-ui/react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { listPromptSourceReports } from "../api/promptSources";
import { usePromptSettings } from "../hooks/usePromptSettings";
import { PromptSourceLoader } from "./PromptSourceLoader";

jest.mock("../api/promptSources", () => ({ listPromptSourceReports: jest.fn() }));

const config = {
  analysis_mode: "llm_grouping",
  extraction: { prompt: "議題に関係する発言だけを抽出する" },
  hierarchical_overview: { prompt: "グループの議論を要約する" },
};

function Harness() {
  const promptSettings = usePromptSettings();
  return (
    <ChakraProvider value={system}>
      <PromptSourceLoader promptSettings={promptSettings} />
      <Textarea
        aria-label="抽出プロンプト"
        value={promptSettings.extraction}
        onChange={(e) => promptSettings.setExtraction(e.target.value)}
      />
      <Textarea
        aria-label="要約プロンプト"
        value={promptSettings.overview}
        onChange={(e) => promptSettings.setOverview(e.target.value)}
      />
    </ChakraProvider>
  );
}

const mockFetch = jest.fn();

beforeEach(() => {
  jest.clearAllMocks();
  global.fetch = mockFetch;
  jest.mocked(listPromptSourceReports).mockResolvedValue({
    success: true,
    reports: [{ slug: "group-a", title: "グループA", createdAt: "2026-11-01T00:00:00Z" }],
  });
  mockFetch.mockResolvedValue({ ok: true, json: async () => ({ config }) });
});

const selectReport = async (user: ReturnType<typeof userEvent.setup>) => {
  const select = screen.getByLabelText("プロンプトを読み込むレポート");
  await screen.findByRole("option", { name: "グループA（group-a）" });
  await user.selectOptions(select, "group-a");
  await user.click(screen.getByRole("button", { name: "読み込む" }));
};

it("既定のままなら確認なしで読み込み、読み込み元と読み込まなかった工程を示す", async () => {
  const user = userEvent.setup();
  render(<Harness />);
  await selectReport(user);

  expect(await screen.findByText("「グループA（group-a）」から抽出・要約プロンプトを読み込みました。")).toBeVisible();
  expect(mockFetch).toHaveBeenCalledWith("/api/admin/reports/group-a/config");
  expect(screen.getByLabelText("抽出プロンプト")).toHaveValue("議題に関係する発言だけを抽出する");
  expect(screen.getByLabelText("要約プロンプト")).toHaveValue("グループの議論を要約する");
  expect(
    screen.getByText(
      "初期ラベリング・統合ラベリングプロンプトはこのレポートに保存されていないため、今の内容のままです。",
    ),
  ).toBeVisible();

  await user.type(screen.getByLabelText("抽出プロンプト"), "（追記）");
  expect(screen.getByText("読み込んだ後に抽出プロンプトを編集しています。")).toBeVisible();
});

it("入力済みのプロンプトは確認してから上書きし、やめれば残す", async () => {
  const user = userEvent.setup();
  render(<Harness />);
  const extraction = screen.getByLabelText("抽出プロンプト");
  await user.clear(extraction);
  await user.type(extraction, "自分で書いた抽出");

  await selectReport(user);
  expect(
    await screen.findByText("入力済みの抽出プロンプトを「グループA（group-a）」の内容で上書きします。よろしいですか？"),
  ).toBeVisible();
  await user.click(screen.getByRole("button", { name: "やめる" }));
  expect(extraction).toHaveValue("自分で書いた抽出");

  await user.click(screen.getByRole("button", { name: "読み込む" }));
  await user.click(await screen.findByRole("button", { name: "上書きする" }));
  expect(extraction).toHaveValue("議題に関係する発言だけを抽出する");
});

it("確認を出した後に書き換えた欄があれば、上書きする前に確認を出し直す", async () => {
  const user = userEvent.setup();
  render(<Harness />);
  const extraction = screen.getByLabelText("抽出プロンプト");
  const overview = screen.getByLabelText("要約プロンプト");
  await user.clear(extraction);
  await user.type(extraction, "自分で書いた抽出");

  await selectReport(user);
  expect(
    await screen.findByText("入力済みの抽出プロンプトを「グループA（group-a）」の内容で上書きします。よろしいですか？"),
  ).toBeVisible();

  await user.clear(overview);
  await user.type(overview, "自分の要約");
  await user.click(screen.getByRole("button", { name: "上書きする" }));
  expect(
    await screen.findByText(
      "入力済みの抽出・要約プロンプトを「グループA（group-a）」の内容で上書きします。よろしいですか？",
    ),
  ).toBeVisible();
  expect(overview).toHaveValue("自分の要約");
  expect(extraction).toHaveValue("自分で書いた抽出");

  await user.click(screen.getByRole("button", { name: "上書きする" }));
  expect(extraction).toHaveValue("議題に関係する発言だけを抽出する");
  expect(overview).toHaveValue("グループの議論を要約する");
});

it("設定の取得に失敗したらプロンプトを変えずに理由を示す", async () => {
  mockFetch.mockResolvedValue({ ok: false, json: async () => ({ detail: "Config file not found" }) });
  const user = userEvent.setup();
  render(<Harness />);
  const before = (screen.getByLabelText("抽出プロンプト") as HTMLTextAreaElement).value;
  await selectReport(user);

  expect(await screen.findByRole("alert")).toHaveTextContent(
    "「グループA（group-a）」の設定を取得できませんでした（Config file not found）。プロンプトは変わっていません。",
  );
  expect(screen.getByLabelText("抽出プロンプト")).toHaveValue(before);
});

it("一覧の取得に失敗したら再試行でき、レポートが無ければその旨を示す", async () => {
  jest
    .mocked(listPromptSourceReports)
    .mockResolvedValueOnce({ success: false, error: "接続できません" })
    .mockResolvedValueOnce({ success: true, reports: [] });
  const user = userEvent.setup();
  render(<Harness />);

  expect(await screen.findByText("レポート一覧を取得できませんでした（接続できません）。")).toBeVisible();
  await user.click(screen.getByRole("button", { name: "再試行" }));
  await waitFor(() => expect(screen.getByText("読み込めるレポートがまだありません。")).toBeVisible());
  expect(screen.getByRole("button", { name: "読み込む" })).toBeDisabled();
});
