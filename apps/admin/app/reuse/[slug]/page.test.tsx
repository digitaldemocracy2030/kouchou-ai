import { duplicateReport } from "@/app/_components/ReportCard/DuplicateReportDialog/actions";
import { system } from "@/components/theme/system";
import { ChakraProvider } from "@chakra-ui/react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import Page from "./page";

jest.mock("@/app/_components/ReportCard/DuplicateReportDialog/actions", () => ({ duplicateReport: jest.fn() }));
jest.mock("next/navigation", () => ({ useRouter: () => ({ push: jest.fn() }) }));
jest.mock("@/components/Header", () => ({ Header: () => null }));
jest.mock("@/components/ui/toaster", () => ({ toaster: { create: jest.fn() } }));
jest.mock("@/app/create/components/ClusterSettingsSection", () => ({ ClusterSettingsSection: () => null }));
jest.mock("@/app/create/components/EnvironmentCheckDialog/EnvironmentCheckDialog", () => ({
  EnvironmentCheckDialog: () => null,
}));

const sourceConfig = {
  question: "元の問い",
  intro: "",
  provider: "openai",
  model: "gpt-4o-mini",
  analysis_mode: "llm_grouping",
  llm_grouping: { discovery_sample_size: 200, assignment_batch_size: 40 },
  hierarchical_clustering: { cluster_nums: [3, 6] },
};

beforeEach(() => {
  jest.clearAllMocks();
  window.localStorage.clear();
  global.fetch = jest.fn(async (url) => {
    if (String(url).includes("/config")) {
      return { ok: true, json: async () => ({ config: sourceConfig }) } as Response;
    }
    return { ok: true, json: async () => [] } as Response;
  });
  jest.mocked(duplicateReport).mockResolvedValue({ success: true, slug: "src-copy" });
});

it("再利用元の分析方式を表示し、override に含まれない分析方式は変更できない", async () => {
  const user = userEvent.setup();
  render(
    <ChakraProvider value={system}>
      <Page params={Promise.resolve({ slug: "src" })} />
    </ChakraProvider>,
  );

  await waitFor(() => expect(screen.getByRole("button", { name: "再利用を開始" })).toBeEnabled());
  await user.click(screen.getByRole("button", { name: "レポート生成設定" }));

  const mode = await screen.findByRole("combobox", { name: "分析方式" });
  expect(mode).toHaveValue("llm_grouping");
  expect(mode).toBeDisabled();
  expect(screen.getByText(/再利用元レポートの分析方式を引き継ぎます/)).toBeInTheDocument();
});

it("再利用元の件数を表示し、全件一括へ切り替えて再利用できる", async () => {
  const user = userEvent.setup();
  render(
    <ChakraProvider value={system}>
      <Page params={Promise.resolve({ slug: "src" })} />
    </ChakraProvider>,
  );
  const start = screen.getByRole("button", { name: "再利用を開始" });
  await waitFor(() => expect(start).toBeEnabled());
  await user.click(screen.getByRole("button", { name: "レポート生成設定" }));

  expect(await screen.findByRole("spinbutton", { name: "分類枠を作るサンプル数" })).toHaveValue(200);
  expect(screen.getByRole("spinbutton", { name: "割り当て1回あたりの件数" })).toHaveValue(40);
  await user.click(screen.getByRole("checkbox", { name: "全件を一度に読む（Long Context）" }));
  fireEvent.click(start);

  expect(duplicateReport).toHaveBeenCalledWith(
    "src",
    expect.objectContaining({
      overrides: expect.objectContaining({ llm_grouping: { use_all_arguments: true } }),
    }),
  );
});
