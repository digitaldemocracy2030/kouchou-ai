import { system } from "@/components/theme/system";
import type { Report } from "@/type";
import { ChakraProvider } from "@chakra-ui/react";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { DuplicateReportDialog } from "./DuplicateReportDialog";

jest.mock("lucide-react", () => ({ ChevronRightIcon: () => null }));
jest.mock("next/navigation", () => ({ useRouter: () => ({ refresh: jest.fn() }) }));
jest.mock("./actions", () => ({ duplicateReport: jest.fn() }));
jest.mock("@/components/ui/toaster", () => ({ toaster: { create: jest.fn() } }));
const serverCatalog = require("../../../../../api/src/services/model_catalog.json");

it("複製画面も廃止済み設定を保ち、新モデルを未確認で選択できる", async () => {
  global.fetch = jest.fn(async (url) => {
    if (String(url).endsWith("/config"))
      return {
        ok: true,
        json: async () => ({
          config: {
            provider: "gemini",
            model: "gemini-1.5-pro",
            question: "Test",
            intro: "",
            hierarchical_clustering: { cluster_nums: [5, 50] },
          },
        }),
      } as Response;
    const provider = new URL(String(url), "http://localhost").searchParams.get("provider");
    return {
      ok: true,
      json: async () =>
        provider === "azure"
          ? [{ value: "azure-server", label: "サーバー設定を使用" }]
          : serverCatalog.filter((r: { provider: string }) => r.provider === provider),
    } as Response;
  });
  const user = userEvent.setup();
  render(
    <ChakraProvider value={system}>
      <DuplicateReportDialog report={{ slug: "example" } as Report} isOpen={true} setIsOpen={jest.fn()} />
    </ChakraProvider>,
  );
  await screen.findByRole("option", { name: "Gemini 3.8 Flash（動作未確認）" });
  const [provider, model] = screen.getAllByRole("combobox");
  expect(model).toHaveValue("gemini-1.5-pro");
  expect(screen.getByText(/このモデルは利用できません/)).toBeInTheDocument();
  await user.selectOptions(model, "gemini-3.8-flash");
  expect(model).toHaveValue("gemini-3.8-flash");
  await user.selectOptions(provider, "azure");
  await waitFor(() => expect(model).toBeDisabled());
  expect(provider).toBeEnabled();
  await user.selectOptions(provider, "openai");
  await screen.findByRole("option", { name: "GPT-5.6 Luna（動作未確認）" });
  expect(model).toBeEnabled();
});
