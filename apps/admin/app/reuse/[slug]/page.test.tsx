import { duplicateReport } from "@/app/_components/ReportCard/DuplicateReportDialog/actions";
import { system } from "@/components/theme/system";
import { ChakraProvider } from "@chakra-ui/react";
import { render, screen, waitFor } from "@testing-library/react";
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
