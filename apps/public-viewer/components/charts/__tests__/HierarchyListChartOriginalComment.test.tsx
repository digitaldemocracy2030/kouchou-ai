import "@testing-library/jest-dom";
import { Provider } from "@/components/ui/provider";
import type { Argument, Cluster, Comments, Config } from "@/type";
import { fireEvent, render, screen } from "@testing-library/react";
import { HierarchyListChart } from "../HierarchyListChart";

globalThis.structuredClone ??= <T,>(value: T): T => (value === undefined ? value : JSON.parse(JSON.stringify(value)));

// lucide-react は ESM のみ配布のため空コンポーネントに差し替える
jest.mock("lucide-react", () => new Proxy({}, { get: (_, name) => (name === "__esModule" ? true : () => null) }));

const clusters: Cluster[] = [
  { level: 0, id: "0", label: "全体", takeaway: "", value: 3, parent: "", density_rank_percentile: 0.5 },
  { level: 1, id: "1_1", label: "第一階層", takeaway: "", value: 3, parent: "0", density_rank_percentile: 0.5 },
  { level: 2, id: "2_1", label: "最下層", takeaway: "", value: 3, parent: "1_1", density_rank_percentile: 0.5 },
];
const first: Argument = {
  arg_id: "A1",
  argument: "意見 A1",
  comment_id: 1,
  x: 0,
  y: 0,
  p: 0,
  cluster_ids: ["0", "1_1", "2_1"],
};
const args: Argument[] = [
  first,
  { ...first, arg_id: "A2", argument: "意見 A2", comment_id: "extra", comment_ids: ["1", "2", "2", "missing"] },
  { ...first, arg_id: "A3", argument: "意見 A3", comment_id: "extra", comment_ids: [] },
];
const comments: Comments = {
  "1": { comment: "共有の元コメント本文" },
  "2": { comment: "A2 の二つ目の元コメント本文" },
  extra: { comment: "参照されていない本文" },
};

function renderList(config: Config | undefined, filteredArgumentIds?: string[], sourceComments?: Comments) {
  render(
    <Provider>
      <HierarchyListChart
        clusterList={clusters}
        argumentList={args}
        config={config}
        comments={sourceComments ?? comments}
        filteredArgumentIds={filteredArgumentIds}
      />
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
  it("公開された複数出典を重複なく折りたたみ、欠けた本文を案内する", async () => {
    renderList({ enable_original_comments: true } as Config);
    expect(screen.getByText("意見 A1")).toBeInTheDocument();
    expect(screen.getByText("意見 A2")).toBeInTheDocument();
    expect(screen.getByRole("region", { name: "元コメント 2件" })).toBeInTheDocument();
    expect(screen.queryByText("共有の元コメント本文")).not.toBeInTheDocument();
    fireEvent.click(screen.getByText("元コメント 1", { exact: true }));
    fireEvent.click(screen.getByText("元コメント 2", { exact: true }));
    expect(await screen.findAllByText("共有の元コメント本文")).toHaveLength(1);
    expect(await screen.findByText("A2 の二つ目の元コメント本文")).toBeVisible();
    expect(screen.getByText("一部の元コメント本文はこのレポートに含まれていません。")).toBeInTheDocument();
    expect(screen.queryByText("参照されていない本文")).not.toBeInTheDocument();
  });

  it("公開を明示していないレポートでは、comments があっても本文を出さない", () => {
    renderList({} as Config);
    expect(screen.getByText("意見 A1")).toBeInTheDocument();
    expect(screen.getByText("このレポートでは元コメント本文を公開していません。")).toBeInTheDocument();
    expect(screen.queryByText("元コメント 1", { exact: true })).not.toBeInTheDocument();
  });

  it("属性で絞り込むと、一致した意見の出典だけを出す", async () => {
    renderList({ enable_original_comments: true } as Config, ["A1"]);
    expect(screen.getByRole("region", { name: "元コメント 1件" })).toBeInTheDocument();
    fireEvent.click(screen.getByText("元コメント 1", { exact: true }));
    expect(await screen.findByText("共有の元コメント本文")).toBeVisible();
    expect(screen.queryByText("元コメント 2", { exact: true })).not.toBeInTheDocument();
  });

  it("公開を指定しても本文がない場合は、本文が欠けていることを案内する", () => {
    renderList({ enable_original_comments: true } as Config, undefined, {});
    expect(screen.getByText("元コメント本文はこのレポートに含まれていません。")).toBeInTheDocument();
  });
});
