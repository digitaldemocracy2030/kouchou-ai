import { system } from "@/components/theme/system";
import type { Report } from "@/type";
import { ReportVisibility } from "@/type";
import { ChakraProvider } from "@chakra-ui/react";
import { act, render, screen } from "@testing-library/react";
import { ReportCard } from "./ReportCard";

// Next の useRouter は refresh の前後で同じオブジェクトを返すので、mock も安定した 1 つのオブジェクトにする
const mockRouter = { refresh: jest.fn() };
jest.mock("next/navigation", () => ({ useRouter: () => mockRouter }));
jest.mock("lucide-react", () => new Proxy({}, { get: (_, name) => (name === "__esModule" ? true : () => null) }));
// ready のカードのメニュー・ダイアログ類は、この確認に関係しないので描画しない
jest.mock("./ActionMenu/ActionMenu", () => ({ ActionMenu: () => null }));
jest.mock("./Visibility/Visibility", () => ({ Visibility: () => null }));
jest.mock("./TokenUsage/TokenUsage", () => ({ TokenUsage: () => null }));
jest.mock("./ReportEditDialog/ReportEditDialog", () => ({ ReportEditDialog: () => null }));
jest.mock("./ClusterEditDialog/ClusterEditDialog", () => ({ ClusterEditDialog: () => null }));
jest.mock("./VisualizationConfigDialog/VisualizationConfigDialog", () => ({ VisualizationConfigDialog: () => null }));

const PROCESSING_TEXT = "AIによるレポート作成中です。完了までしばらくお待ちください。";
const UPLOAD_FAILED_ERROR = "Failed to upload report artifacts to storage";

const processingReport: Report = {
  slug: "demo",
  status: "processing",
  title: "テストレポート",
  description: "",
  isPubcom: false,
  visibility: ReportVisibility.PUBLIC,
  createdAt: "2026-10-19T00:00:00+00:00",
};
const readyReport: Report = {
  ...processingReport,
  status: "ready",
  analysis: { commentNum: 10, argumentsNum: 20, clusterNum: 3 },
};
const errorReport: Report = { ...processingReport, status: "error" };

function stepJson(body: Record<string, unknown>) {
  return { ok: true, json: async () => body } as Response;
}

function renderCard(report: Report) {
  const view = render(
    <ChakraProvider value={system}>
      <ReportCard report={report} />
    </ChakraProvider>,
  );
  // router.refresh() で取り直した一覧の内容でカードを描画し直す
  return (next: Report) =>
    view.rerender(
      <ChakraProvider value={system}>
        <ReportCard report={next} />
      </ChakraProvider>,
    );
}

// ポーリング応答の反映と、それを受けて effect が登録するタイマーが順に進むよう、区切って進める
async function advance(ms: number, step = 100) {
  for (let elapsed = 0; elapsed < ms; elapsed += step) {
    await act(async () => {
      await jest.advanceTimersByTimeAsync(step);
    });
  }
}

describe("ReportCard の進捗表示と一覧の取り直し", () => {
  beforeEach(() => {
    jest.useFakeTimers();
    mockRouter.refresh.mockClear();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it("step-json が completed になっても、一覧が processing の間は取り直しを続け、ready になったら止める", async () => {
    // analysis-core は completed を書き終えたが、API は成果物をアップロード中で一覧はまだ processing
    global.fetch = jest.fn(async () => stepJson({ status: "completed", current_step: "completed" }));
    const rerenderCard = renderCard(processingReport);

    await advance(1500);
    expect(mockRouter.refresh).toHaveBeenCalledTimes(1);

    // 取り直した一覧ではまだ processing（アップロードが終わっていない）
    rerenderCard({ ...processingReport });
    await advance(3000);
    expect(mockRouter.refresh).toHaveBeenCalledTimes(2);
    expect(screen.getByText(PROCESSING_TEXT)).toBeInTheDocument();

    // 次の取り直しの直前に、アップロードが終わって一覧が ready になる。ProgressSteps は退場アニメーションの間
    // 古い props（processing）のまま残るが、その間も含めて取り直しをやめる
    await advance(2500);
    rerenderCard(readyReport);
    await advance(30_000, 1000);
    expect(mockRouter.refresh).toHaveBeenCalledTimes(2);
    expect(screen.queryByText(PROCESSING_TEXT)).not.toBeInTheDocument();
    expect(global.fetch).toHaveBeenCalledTimes(1);
  });

  it("step-json が error になっても、一覧が processing の間は取り直しを続け、error になったら止める", async () => {
    // analysis-core は error を書いたが、API がプロセスの終了を待っている間、一覧はまだ processing
    global.fetch = jest.fn(async () =>
      stepJson({ status: "error", current_step: "hierarchical_initial_labelling", error_message: "rate limit" }),
    );
    const rerenderCard = renderCard(processingReport);

    await advance(1500);
    expect(mockRouter.refresh).toHaveBeenCalledTimes(1);
    expect(screen.getByText("rate limit")).toBeInTheDocument();

    rerenderCard({ ...processingReport });
    await advance(3000);
    expect(mockRouter.refresh).toHaveBeenCalledTimes(2);

    rerenderCard(errorReport);
    await advance(30_000, 1000);
    expect(mockRouter.refresh).toHaveBeenCalledTimes(2);
    expect(screen.getByText("エラーが発生しました。レポート生成設定を調整してください。")).toBeInTheDocument();
    expect(screen.getByText("rate limit")).toBeInTheDocument();
    expect(global.fetch).toHaveBeenCalledTimes(1);
  });

  it("一覧が processing のまま変わらなくても、取り直しは上限で止まる", async () => {
    global.fetch = jest.fn(async () => stepJson({ status: "completed", current_step: "completed" }));
    renderCard(processingReport);

    await advance(1500);
    await advance(10 * 60_000, 10_000);
    const refreshCount = mockRouter.refresh.mock.calls.length;
    expect(refreshCount).toBeGreaterThan(1);

    await advance(10 * 60_000, 10_000);
    expect(mockRouter.refresh).toHaveBeenCalledTimes(refreshCount);
  });

  it("completed の後に一覧が error になったら（成果物のアップロード失敗）、step-json を取り直してエラー理由を表示する", async () => {
    global.fetch = jest
      .fn()
      .mockResolvedValueOnce(stepJson({ status: "completed", current_step: "completed" }))
      .mockResolvedValue(
        stepJson({ status: "error", current_step: "hierarchical_visualization", error_message: UPLOAD_FAILED_ERROR }),
      );
    const rerenderCard = renderCard(processingReport);

    await advance(1500);
    expect(mockRouter.refresh).toHaveBeenCalledTimes(1);

    rerenderCard(errorReport);
    await advance(1000);
    expect(global.fetch).toHaveBeenCalledTimes(2);
    expect(screen.getByText(UPLOAD_FAILED_ERROR)).toBeInTheDocument();

    // error のカードでは、取り直しも step-json のポーリングも続けない
    await advance(30_000, 1000);
    expect(mockRouter.refresh).toHaveBeenCalledTimes(1);
    expect(global.fetch).toHaveBeenCalledTimes(2);
  });

  it("error のカードは ProgressSteps が残っていても、一覧を取り直さない", async () => {
    global.fetch = jest.fn(async () =>
      stepJson({ status: "error", current_step: "hierarchical_initial_labelling", error_message: "rate limit" }),
    );
    renderCard(errorReport);

    await advance(1500);
    expect(screen.getByText("rate limit")).toBeInTheDocument();

    await advance(60_000, 1000);
    expect(mockRouter.refresh).not.toHaveBeenCalled();
    expect(global.fetch).toHaveBeenCalledTimes(1);
  });
});
