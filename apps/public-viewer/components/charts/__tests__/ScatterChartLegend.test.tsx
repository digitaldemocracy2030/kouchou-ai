import "@testing-library/jest-dom";
import { Provider } from "@/components/ui/provider";
import { LanguageProvider } from "@/lib/i18n/LanguageContext";
import type { Argument, Cluster } from "@/type";
import { act, render, screen } from "@testing-library/react";
import { ScatterChart } from "../ScatterChart";

// jsdom には structuredClone が無く、Chakra v3 の recipe 処理が必要とするため補う
globalThis.structuredClone ??= <T,>(value: T): T => (value === undefined ? value : JSON.parse(JSON.stringify(value)));

// Plotly を実描画しないよう ChartCore をモックする（凡例の検証だけが目的のため）
jest.mock("../ChartCore", () => ({
  ChartCore: () => null,
}));

// lucide-react は ESM のみ配布のため空コンポーネントに差し替える
jest.mock("lucide-react", () => new Proxy({}, { get: (_, name) => (name === "__esModule" ? true : () => null) }));

const cluster = (id: string, level: number, parent = ""): Cluster => ({
  id,
  level,
  label: `cluster-${id}`,
  takeaway: "",
  value: 10,
  parent,
  density_rank_percentile: 0.1,
});

const arg = (argId: string, clusterIds: string[]): Argument => ({
  arg_id: argId,
  argument: `arg-${argId}`,
  comment_id: 0,
  x: 0,
  y: 0,
  p: 0,
  cluster_ids: clusterIds,
});

// 第一階層 p1 の下に、最深階層の濃いグループ c1 / c2 がぶら下がる構成
const clusters = [cluster("p1", 1), cluster("c1", 2, "p1"), cluster("c2", 2, "p1")];
const args = [arg("a1", ["p1", "c1"]), arg("a2", ["p1", "c2"])];

function renderChart(props: Partial<React.ComponentProps<typeof ScatterChart>> = {}) {
  return render(
    <Provider>
      <ScatterChart clusterList={clusters} argumentList={args} targetLevel={2} showParentAttribution {...props} />
    </Provider>,
  );
}

describe("ScatterChart attribution legend", () => {
  it("第一階層クラスタ名をグルーピング見出しとして表示する", () => {
    renderChart();
    expect(screen.getByText("cluster-p1")).toBeInTheDocument();
  });

  it("フィルタで全点が除外された濃いグループは凡例で「（非表示）」を付す", () => {
    // a1 のみ残す → c1 は表示対象あり、c2 は表示対象 0 件（plot ではグレー化）
    renderChart({ filteredArgumentIds: ["a1"] });

    expect(screen.getByText("cluster-c2（非表示）")).toBeInTheDocument();
    // 表示対象が残っている c1 には「（非表示）」が付かない
    expect(screen.queryByText("cluster-c1（非表示）")).not.toBeInTheDocument();
    expect(screen.getByText("cluster-c1")).toBeInTheDocument();
  });

  it("フィルタ未適用時はどのグループにも「（非表示）」を付さない", () => {
    renderChart();
    expect(screen.queryByText(/（非表示）/)).not.toBeInTheDocument();
  });

  it("表示言語が英語なら、凡例の見出し・非表示の印・操作ヒントのボタン名も英語になる", async () => {
    window.history.replaceState(null, "", "/report-1?lang=en");
    try {
      await act(async () => {
        render(
          <Provider>
            <LanguageProvider>
              <ScatterChart
                clusterList={clusters}
                argumentList={args}
                targetLevel={2}
                showParentAttribution
                filteredArgumentIds={["a1"]}
              />
            </LanguageProvider>
          </Provider>,
        );
      });
      expect(screen.getByText("Top-level cluster of each dense opinion group")).toBeInTheDocument();
      expect(screen.getByText("cluster-c2 (hidden)")).toBeInTheDocument();
      expect(screen.getByRole("button", { name: "Show how to use the scatter plot" })).toBeInTheDocument();
    } finally {
      window.history.replaceState(null, "", "/");
    }
  });
});
