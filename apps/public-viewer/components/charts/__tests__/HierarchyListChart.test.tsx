import { Provider } from "@/components/ui/provider";
import type { Argument, Cluster } from "@/type";
import { fireEvent, render, screen } from "@testing-library/react";
import { HierarchyListChart } from "../HierarchyListChart";

// jsdom には structuredClone が無く、Chakra v3 の recipe 処理が必要とするため補う
globalThis.structuredClone ??= <T,>(value: T): T => (value === undefined ? value : JSON.parse(JSON.stringify(value)));
jest.mock("lucide-react", () => new Proxy({}, { get: (_, name) => (name === "__esModule" ? true : () => null) }));

function cluster(id: string, level: number, parent: string, value: number): Cluster {
  return { id, level, parent, label: `ラベル ${id}`, takeaway: `説明 ${id}`, value, density_rank_percentile: 0 };
}

const clusters: Cluster[] = [
  cluster("0", 0, "", 4),
  cluster("1_1", 1, "0", 3),
  cluster("1_2", 1, "0", 1),
  cluster("2_1", 2, "1_1", 3),
  cluster("2_2", 2, "1_2", 1),
];

const args: Argument[] = [
  { arg_id: "A1", argument: "意見 A1", comment_id: 1, x: 0, y: 0, p: 0, cluster_ids: ["0", "1_1", "2_1"] },
  { arg_id: "A2", argument: "意見 A2", comment_id: 2, x: 0, y: 0, p: 0, cluster_ids: ["0", "1_1", "2_1"] },
  { arg_id: "A3", argument: "意見 A3", comment_id: 3, x: 0, y: 0, p: 0, cluster_ids: ["0", "1_1", "2_1"] },
  { arg_id: "A4", argument: "意見 A4", comment_id: 4, x: 0, y: 0, p: 0, cluster_ids: ["0", "1_2", "2_2"] },
] as Argument[];

function renderList(props: { clusterList: Cluster[]; filteredArgumentIds?: string[] }) {
  const view = render(
    <Provider>
      <HierarchyListChart
        clusterList={props.clusterList}
        argumentList={args}
        filteredArgumentIds={props.filteredArgumentIds}
      />
    </Provider>,
  );
  return (next: { clusterList: Cluster[]; filteredArgumentIds?: string[] }) =>
    view.rerender(
      <Provider>
        <HierarchyListChart
          clusterList={next.clusterList}
          argumentList={args}
          filteredArgumentIds={next.filteredArgumentIds}
        />
      </Provider>,
    );
}

const expandedCount = () => screen.queryAllByRole("button", { name: "折りたたむ" }).length;

// 「全体」→ 子要素を表示 → 大分類 1_1 → 子要素を表示 → 2_1 → 個別データを表示、まで開く
function expandDown() {
  fireEvent.click(screen.getAllByRole("button", { name: "展開する" })[0]);
  fireEvent.click(screen.getByText(/子要素を表示/));
  fireEvent.click(screen.getAllByRole("button", { name: "展開する" })[0]);
  fireEvent.click(screen.getByText(/子要素を表示/));
  fireEvent.click(screen.getAllByRole("button", { name: "展開する" })[0]);
  fireEvent.click(screen.getByText(/個別データを表示/));
}

describe("HierarchyListChart の展開状態", () => {
  it("フィルタの適用・変更・解除で clusterList が新しい配列になっても、展開状態を保つ", () => {
    const rerender = renderList({ clusterList: clusters });
    expandDown();
    expect(expandedCount()).toBe(3);
    expect(screen.getByText("意見 A1")).toBeInTheDocument();

    // フィルタ適用（ClientContainer の filteredResult は毎回新しい配列を渡す）
    rerender({ clusterList: clusters.map((c) => ({ ...c })), filteredArgumentIds: ["A1"] });
    expect(expandedCount()).toBe(3);
    expect(screen.getByText("意見 A1")).toBeInTheDocument();

    // フィルタ解除
    rerender({ clusterList: [...clusters] });
    expect(expandedCount()).toBe(3);
    expect(screen.getByText("意見 A2")).toBeInTheDocument();
  });

  it("親を閉じたら子孫も閉じ、開き直したときに子孫は閉じたまま", () => {
    renderList({ clusterList: clusters });
    expandDown();
    expect(expandedCount()).toBe(3);

    // 「全体」を閉じる
    fireEvent.click(screen.getAllByRole("button", { name: "折りたたむ" })[0]);
    expect(expandedCount()).toBe(0);

    // 開き直すと「全体」だけが開き、子要素も子孫も閉じたまま
    fireEvent.click(screen.getAllByRole("button", { name: "展開する" })[0]);
    expect(expandedCount()).toBe(1);
    expect(screen.getByText(/子要素を表示/)).toBeInTheDocument();
    fireEvent.click(screen.getByText(/子要素を表示/));
    expect(expandedCount()).toBe(1);
    expect(screen.queryByText("意見 A1")).not.toBeInTheDocument();
  });
});
