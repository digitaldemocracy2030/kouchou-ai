import { system } from "@/components/theme/system";
import { ChakraProvider } from "@chakra-ui/react";
import { act, render, screen } from "@testing-library/react";
import { ProgressSteps } from "./ProgressSteps";

jest.mock("next/navigation", () => ({ useRouter: () => ({ refresh: jest.fn() }) }));
jest.mock("lucide-react", () => new Proxy({}, { get: (_, name) => (name === "__esModule" ? true : () => null) }));

const LLM_GROUPING_STEPS = [
  "extraction",
  "embedding",
  "llm_grouping",
  "hierarchical_overview",
  "hierarchical_aggregation",
];

function stepJson(body: Record<string, unknown>) {
  return { ok: true, json: async () => body } as Response;
}

function renderSteps(responses: Record<string, unknown>[], reportStatus: "processing" | "error" = "processing") {
  const fetchMock = jest.fn();
  for (const body of responses) {
    fetchMock.mockResolvedValueOnce(stepJson(body));
  }
  global.fetch = fetchMock;
  render(
    <ChakraProvider value={system}>
      <ProgressSteps slug="demo" reportStatus={reportStatus} />
    </ChakraProvider>,
  );
}

// ポーリング応答の反映と、次のポーリングのタイマーが順に進むよう、区切って進める
async function advance(ms: number, step = 100) {
  for (let elapsed = 0; elapsed < ms; elapsed += step) {
    await act(async () => {
      await jest.advanceTimersByTimeAsync(step);
    });
  }
}

function stepStates() {
  return Object.fromEntries(
    screen
      .getAllByTestId("progress-step")
      .map((item) => [item.getAttribute("data-step-key"), item.getAttribute("data-step-state")]),
  );
}

describe("ProgressSteps の工程表示", () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  it("llm_grouping の実行中は、API が返した工程で「LLM直接グルーピング」を実行中として示す", async () => {
    renderSteps([
      { status: "running", current_step: "embedding", steps: LLM_GROUPING_STEPS },
      { status: "running", current_step: "llm_grouping", steps: LLM_GROUPING_STEPS },
      { status: "running", current_step: "llm_grouping", steps: LLM_GROUPING_STEPS },
    ]);
    await advance(3500);

    expect(screen.getByText("LLM直接グルーピング")).toBeInTheDocument();
    expect(screen.queryByText("意見グループ化")).not.toBeInTheDocument();
    expect(screen.queryByText("初期ラベリング")).not.toBeInTheDocument();
    expect(stepStates()).toEqual({
      extraction: "completed",
      embedding: "completed",
      llm_grouping: "current",
      hierarchical_overview: "pending",
      hierarchical_aggregation: "pending",
    });
  });

  it("llm_grouping で失敗したら、失敗マークは「埋め込み」ではなく「LLM直接グルーピング」に付く", async () => {
    renderSteps([
      { status: "running", current_step: "embedding", steps: LLM_GROUPING_STEPS },
      { status: "running", current_step: "llm_grouping", steps: LLM_GROUPING_STEPS },
      {
        status: "error",
        current_step: "llm_grouping",
        steps: LLM_GROUPING_STEPS,
        error_message: "Step 'llm_grouping' failed: llm_grouping group discovery returned no groups",
      },
    ]);
    await advance(7000);

    expect(screen.getByRole("alert")).toHaveTextContent("group discovery returned no groups");
    expect(stepStates()).toMatchObject({ embedding: "completed", llm_grouping: "failed" });
  });

  it("エラーのカードを開き直したときも、失敗した工程に失敗マークが付く（「抽出」に倒さない）", async () => {
    renderSteps(
      [{ status: "error", current_step: "llm_grouping", steps: LLM_GROUPING_STEPS, error_message: "failed" }],
      "error",
    );
    await advance(500);

    expect(stepStates()).toMatchObject({ extraction: "completed", embedding: "completed", llm_grouping: "failed" });
  });

  it("llm_grouping の後の概要生成では、llm_grouping モードに無い工程を完了扱いにしない", async () => {
    renderSteps([
      { status: "running", current_step: "llm_grouping", steps: LLM_GROUPING_STEPS },
      { status: "running", current_step: "hierarchical_overview", steps: LLM_GROUPING_STEPS },
    ]);
    await advance(3500);

    const states = Object.values(stepStates());
    expect(states.filter((state) => state === "completed")).toHaveLength(3);
    expect(stepStates().hierarchical_overview).toBe("current");
  });

  it("steps を返さない API でも既定の工程で表示し、知らない工程名は捨てずに表示する", async () => {
    renderSteps([
      { status: "running", current_step: "embedding" },
      { status: "running", current_step: "custom_step" },
    ]);
    await advance(3500);

    expect(screen.getByText("意見グループ化")).toBeInTheDocument();
    expect(screen.getByText("custom_step")).toBeInTheDocument();
    expect(stepStates().custom_step).toBe("current");
  });

  it("工程を受け取る前に状況の取得自体が失敗したら、どの工程にも失敗マークを付けない", async () => {
    const fetchMock = jest.fn().mockResolvedValue({ ok: false } as Response);
    global.fetch = fetchMock;
    jest.spyOn(console, "error").mockImplementation(() => {});
    render(
      <ChakraProvider value={system}>
        <ProgressSteps slug="demo" reportStatus="processing" />
      </ChakraProvider>,
    );
    await advance(60000, 1000);

    expect(screen.getByRole("alert")).toHaveTextContent("レポート生成状況の取得に失敗しました。");
    expect(Object.values(stepStates())).not.toContain("failed");
  });
});
