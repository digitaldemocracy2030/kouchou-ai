import { Provider } from "@/components/ui/provider";
import type { Argument, Cluster, Comments, Config } from "@/type";
import { fireEvent, render, screen } from "@testing-library/react";
import { HierarchyListChart } from "../HierarchyListChart";

globalThis.structuredClone ??= <T,>(value: T): T => (value === undefined ? value : JSON.parse(JSON.stringify(value)));

// lucide-react は ESM のみ配布のため空コンポーネントに差し替える
jest.mock("lucide-react", () => new Proxy({}, { get: (_, name) => (name === "__esModule" ? true : () => null) }));

const clusters: Cluster[] = [
  { level: 0, id: "0", label: "全体", takeaway: "", value: 1, parent: "", density_rank_percentile: 0.5 },
  { level: 1, id: "1_1", label: "第一階層", takeaway: "", value: 1, parent: "0", density_rank_percentile: 0.5 },
  { level: 2, id: "2_1", label: "最下層", takeaway: "", value: 1, parent: "1_1", density_rank_percentile: 0.5 },
];
const args: Argument[] = [
  { arg_id: "A1", argument: "意見 A1", comment_id: 1, x: 0, y: 0, p: 0, cluster_ids: ["0", "1_1", "2_1"] },
];
const comments: Comments = { "1": { comment: "A1 の元コメント本文" } };

function renderList(config: Config | undefined) {
  render(
    <Provider>
      <HierarchyListChart clusterList={clusters} argumentList={args} config={config} comments={comments} />
    </Provider>,
  );
  // 全体 → 第一階層 → 最下層 → 個別データの順に開く（既存の HierarchyListChart.test と同じ操作）
  fireEvent.click(screen.getAllByRole("button", { name: "展開する" })[0]);
  fireEvent.click(screen.getByText(/子要素を表示/));
  fireEvent.click(screen.getAllByRole("button", { name: "展開する" })[0]);
  fireEvent.click(screen.getByText(/子要素を表示/));
  fireEvent.click(screen.getAllByRole("button", { name: "展開する" })[0]);
  fireEvent.click(screen.getByText(/個別データを表示/));
}

describe("HierarchyListChart original comment", () => {
  it("公開を明示したレポートでは、意見の下に元コメント本文を出す", () => {
    renderList({ enable_original_comments: true } as Config);
    expect(screen.getByText("意見 A1")).toBeInTheDocument();
    expect(screen.getByText(/A1 の元コメント本文/)).toBeInTheDocument();
  });

  it("公開を明示していないレポートでは、comments があっても本文を出さない", () => {
    renderList({} as Config);
    expect(screen.getByText("意見 A1")).toBeInTheDocument();
    expect(screen.queryByText(/A1 の元コメント本文/)).not.toBeInTheDocument();
  });
});
