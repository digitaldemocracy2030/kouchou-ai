import "@testing-library/jest-dom";
import { Provider } from "@/components/ui/provider";
import type { Argument, Cluster } from "@/type";
import { fireEvent, render, screen } from "@testing-library/react";
import { HierarchyListChart } from "../HierarchyListChart";

// jsdom には structuredClone が無く、Chakra v3 の recipe 処理が必要とするため補う
globalThis.structuredClone ??= <T,>(value: T): T => (value === undefined ? value : JSON.parse(JSON.stringify(value)));

// lucide-react は ESM のみ配布のため空コンポーネントに差し替える
jest.mock("lucide-react", () => new Proxy({}, { get: (_, name) => (name === "__esModule" ? true : () => null) }));

const cluster = (id: string, level: number, parent: string, value: number): Cluster => ({
  id,
  level,
  parent,
  value,
  label: `L-${id}`,
  takeaway: "",
  density_rank_percentile: 0.5,
});

const arg = (argId: string, clusterIds: string[]): Argument => ({
  arg_id: argId,
  argument: `op ${argId}`,
  comment_id: 0,
  x: 0,
  y: 0,
  p: 0,
  cluster_ids: clusterIds,
});

const clusters: Cluster[] = [
  cluster("0", 0, "", 4),
  cluster("1_0", 1, "0", 3),
  cluster("1_1", 1, "0", 1),
  cluster("2_0", 2, "1_0", 3),
  cluster("2_1", 2, "1_1", 1),
];
const args = [
  arg("A1", ["0", "1_0", "2_0"]),
  arg("A2", ["0", "1_0", "2_0"]),
  arg("A3", ["0", "1_0", "2_0"]),
  arg("A4", ["0", "1_1", "2_1"]),
];

function renderList(filteredArgumentIds?: string[]) {
  return render(
    <Provider>
      <HierarchyListChart clusterList={clusters} argumentList={args} filteredArgumentIds={filteredArgumentIds} />
    </Provider>,
  );
}

function expandRoot() {
  fireEvent.click(screen.getAllByLabelText("展開する")[0]);
  fireEvent.click(screen.getByText(/子要素を表示/));
}

describe("HierarchyListChart のクラスタ件数", () => {
  it("フィルタ中はフィルター後の件数を全件と並べて表示する（ツリーマップ・クラスタ一覧と同じ数え方）", () => {
    renderList(["A1", "A4"]);
    expandRoot();

    expect(screen.getByText("(フィルター後 2件 / 全4件)")).toBeInTheDocument();
    expect(screen.getByText("(フィルター後 1件 / 全3件)")).toBeInTheDocument();
    expect(screen.getByText("(フィルター後 1件 / 全1件)")).toBeInTheDocument();
    expect(screen.queryByText("(4件)")).not.toBeInTheDocument();
  });

  it("一致する意見が無いクラスタは 0 件と表示する", () => {
    renderList(["A4"]);
    expandRoot();

    expect(screen.getByText("(フィルター後 0件 / 全3件)")).toBeInTheDocument();
  });

  it("フィルタなしでは従来どおり全件の件数を表示する", () => {
    renderList();
    expandRoot();

    expect(screen.getByText("(4件)")).toBeInTheDocument();
    expect(screen.getByText("(3件)")).toBeInTheDocument();
    expect(screen.getByText("(1件)")).toBeInTheDocument();
    expect(screen.queryByText(/フィルター後/)).not.toBeInTheDocument();
  });
});
