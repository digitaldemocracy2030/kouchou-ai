import { system } from "@/components/theme/system";
import type { Report, ReportDisplayConfig } from "@/type";
import { ChakraProvider } from "@chakra-ui/react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { VisualizationConfigDialog } from "./VisualizationConfigDialog";
import { fetchVisualizationConfig, updateVisualizationConfig } from "./actions";

jest.mock("./actions", () => ({ fetchVisualizationConfig: jest.fn(), updateVisualizationConfig: jest.fn() }));
jest.mock("@/components/ui/toaster", () => ({ toaster: { create: jest.fn() } }));
const initial: ReportDisplayConfig = {
  version: "1",
  enabledCharts: ["scatterAll", "scatterDensity", "treemap"],
  defaultChart: "treemap",
  chartOrder: ["treemap", "scatterDensity", "scatterAll"],
  params: { showClusterLabels: false, scatterDensity: { maxDensity: 0.4, minValue: 8 } },
};
const mount = () =>
  render(
    <ChakraProvider value={system}>
      <VisualizationConfigDialog
        report={{ slug: "test" } as Report}
        isOpen
        setIsVisualizationConfigDialogOpen={jest.fn()}
      />
    </ChakraProvider>,
  );
beforeEach(() => {
  jest.clearAllMocks();
  jest.mocked(fetchVisualizationConfig).mockResolvedValue({ success: true, config: initial });
  jest.mocked(updateVisualizationConfig).mockResolvedValue({ success: true });
});

test("閾値を保存して開き直せ、他の設定を保持する", async () => {
  const view = mount();
  const percentage = await screen.findByLabelText("表示する密度の上位割合（%）");
  expect(percentage).toHaveValue(40);
  fireEvent.change(percentage, { target: { value: "35" } });
  fireEvent.change(screen.getByLabelText("意見グループの最小サンプル数"), { target: { value: "7" } });
  fireEvent.click(screen.getByRole("button", { name: "保存" }));
  const saved = { ...initial, params: { ...initial.params, scatterDensity: { maxDensity: 0.35, minValue: 7 } } };
  await waitFor(() => expect(updateVisualizationConfig).toHaveBeenCalledWith("test", saved));
  view.unmount();
  jest.mocked(fetchVisualizationConfig).mockResolvedValue({ success: true, config: saved });
  mount();
  expect(await screen.findByLabelText("表示する密度の上位割合（%）")).toHaveValue(35);
  expect(screen.getByLabelText("意見グループの最小サンプル数")).toHaveValue(7);
});

test.each(["", "-1", "101"])("割合%sは保存しない", async (value) => {
  mount();
  fireEvent.change(await screen.findByLabelText("表示する密度の上位割合（%）"), { target: { value } });
  expect(screen.getByRole("button", { name: "保存" })).toBeDisabled();
  expect(updateVisualizationConfig).not.toHaveBeenCalled();
});

test.each(["", "-1", "1.5"])("最小件数%sは保存しない", async (value) => {
  mount();
  fireEvent.change(await screen.findByLabelText("意見グループの最小サンプル数"), { target: { value } });
  expect(screen.getByRole("button", { name: "保存" })).toBeDisabled();
});

test("未設定なら20%・5件を表示する", async () => {
  jest.mocked(fetchVisualizationConfig).mockResolvedValue({ success: true, config: null });
  mount();
  expect(await screen.findByLabelText("表示する密度の上位割合（%）")).toHaveValue(20);
  expect(screen.getByLabelText("意見グループの最小サンプル数")).toHaveValue(5);
});

test("取得失敗時にデフォルト値で既存設定を上書きしない", async () => {
  jest.mocked(fetchVisualizationConfig).mockResolvedValue({ success: false, error: "error" });
  mount();
  await waitFor(() => expect(fetchVisualizationConfig).toHaveBeenCalled());
  expect(screen.queryByRole("button", { name: "保存" })).not.toBeInTheDocument();
  expect(updateVisualizationConfig).not.toHaveBeenCalled();
});
