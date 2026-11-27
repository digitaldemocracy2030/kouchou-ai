import { Provider } from "@/components/ui/provider";
import type { Argument, Cluster, Config } from "@/type";
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

  it("対立ビューから戻ると選んだ話題と祖先を開き、対立ビューを開くボタンにフォーカスを戻す", () => {
    const openOpposition = jest.fn();
    render(
      <Provider>
        <HierarchyListChart
          clusterList={clusters}
          argumentList={args}
          oppositionClusterIds={new Set(["1_1"])}
          onOpenOpposition={openOpposition}
          reopenClusterId="1_1"
        />
      </Provider>,
    );

    expect(expandedCount()).toBe(2);
    const action = screen.getByRole("button", { name: "この話題の対立を見る" });
    expect(action).toHaveFocus();
    fireEvent.click(action);
    expect(openOpposition).toHaveBeenCalledWith("1_1");
  });
});

describe("HierarchyListChart の一括展開（#1206）", () => {
  it("「すべて開く」で全階層と最下層の個別データまで開き、「すべて閉じる」で全部閉じる", () => {
    renderList({ clusterList: clusters });
    expect(expandedCount()).toBe(0);

    fireEvent.click(screen.getByRole("button", { name: "すべて開く" }));
    // 全体・大分類 2 つ・最下層 2 つの 5 グループが開き、両方の枝の個別データが見える
    expect(expandedCount()).toBe(5);
    for (const text of ["意見 A1", "意見 A2", "意見 A3", "意見 A4"]) {
      expect(screen.getByText(text)).toBeInTheDocument();
    }

    fireEvent.click(screen.getByRole("button", { name: "すべて閉じる" }));
    expect(expandedCount()).toBe(0);
    expect(screen.queryByText("意見 A1")).not.toBeInTheDocument();

    // 閉じた後に 1 つ開いても、子孫は閉じたまま
    fireEvent.click(screen.getAllByRole("button", { name: "展開する" })[0]);
    expect(expandedCount()).toBe(1);
  });

  it("一括で開いた状態はフィルタの適用で clusterList が作り直されても保つ", () => {
    const rerender = renderList({ clusterList: clusters });
    fireEvent.click(screen.getByRole("button", { name: "すべて開く" }));
    rerender({ clusterList: clusters.map((c) => ({ ...c })), filteredArgumentIds: ["A4"] });
    expect(expandedCount()).toBe(5);
    expect(screen.getByText("意見 A4")).toBeInTheDocument();
  });
});

describe("HierarchyListChart の出典リンク（#1159）", () => {
  const withUrl: Argument[] = args.map((a) => (a.arg_id === "A1" ? { ...a, url: "https://example.com/a1" } : a));
  const config = { name: "n", question: "q", intro: "i", model: "m" } as unknown as Config;

  function renderWith(enable_source_link: boolean | undefined) {
    render(
      <Provider>
        <HierarchyListChart
          clusterList={clusters}
          argumentList={withUrl}
          config={enable_source_link === undefined ? undefined : { ...config, enable_source_link }}
        />
      </Provider>,
    );
    expandDown();
  }

  it("enable_source_link が有効なら URL のある意見にだけ出典リンクを出す", () => {
    renderWith(true);
    const links = screen.getAllByRole("link", { name: /出典を見る/ });
    expect(links).toHaveLength(1);
    expect(links[0]).toHaveAttribute("href", "https://example.com/a1");
    expect(links[0]).toHaveAttribute("target", "_blank");
    expect(links[0]).toHaveAttribute("rel", "noopener noreferrer");
  });

  it("enable_source_link が無効、または設定が無いなら出典リンクを出さない", () => {
    renderWith(false);
    expect(screen.queryByRole("link", { name: /出典を見る/ })).not.toBeInTheDocument();
  });
});

describe("HierarchyListChart のテキスト検索（#1205）", () => {
  function renderSearch(props: { filteredArgumentIds?: string[]; textSearch?: string; argumentList?: Argument[] }) {
    const element = (p: typeof props) => (
      <Provider>
        <HierarchyListChart
          clusterList={clusters}
          argumentList={p.argumentList ?? args}
          filteredArgumentIds={p.filteredArgumentIds}
          textSearch={p.textSearch}
        />
      </Provider>
    );
    const view = render(element(props));
    return (next: typeof props) => view.rerender(element(next));
  }

  it("検索中は一致した意見を含むグループだけを、最下層の意見まで開く", () => {
    renderSearch({ filteredArgumentIds: ["A4"], textSearch: "A4" });
    // 全体・1_2・2_2 の 3 グループが開き、一致しない 1_1 の枝は閉じたまま
    expect(expandedCount()).toBe(3);
    expect(screen.getByText("意見 A4")).toBeInTheDocument();
    expect(screen.queryByText("意見 A1")).not.toBeInTheDocument();
  });

  it("後から検索しても開き、検索語を変えると新しく一致した枝も開く", () => {
    const rerender = renderSearch({});
    expect(expandedCount()).toBe(0);
    rerender({ filteredArgumentIds: ["A1"], textSearch: "A1" });
    expect(screen.getByText("意見 A1")).toBeInTheDocument();
    rerender({ filteredArgumentIds: ["A4"], textSearch: "A4" });
    expect(screen.getByText("意見 A4")).toBeInTheDocument();
  });

  it("属性フィルタだけ（検索語なし）のときは自動では開かない", () => {
    renderSearch({ filteredArgumentIds: ["A4"] });
    expect(expandedCount()).toBe(0);
  });

  it("一致した意見は、最初の 10 件に入らない位置にあっても先頭に並べて表示する", () => {
    const many: Argument[] = Array.from({ length: 12 }, (_, i) => ({
      arg_id: `M${i}`,
      argument: `意見 M${i}`,
      comment_id: 100 + i,
      x: 0,
      y: 0,
      p: 0,
      cluster_ids: ["0", "1_1", "2_1"],
    })) as Argument[];
    renderSearch({ argumentList: many, filteredArgumentIds: ["M11"], textSearch: "M11" });
    expect(screen.getByText("意見 M11")).toBeInTheDocument();
    // 10 件まで表示し、残り 2 件は「さらに表示」の奥
    expect(screen.getByText(/さらに表示/)).toBeInTheDocument();
    expect(screen.queryByText("意見 M10")).not.toBeInTheDocument();
  });
});

describe("HierarchyListChart の指定グループを開いた表示（#1207）", () => {
  const originalScrollIntoView = Element.prototype.scrollIntoView;
  let scrollIntoView: jest.Mock;
  beforeEach(() => {
    scrollIntoView = jest.fn();
    Element.prototype.scrollIntoView = scrollIntoView;
  });
  afterEach(() => {
    Element.prototype.scrollIntoView = originalScrollIntoView;
  });

  it("散布図から移ってきたグループと祖先を開き、そのグループは最下層の意見まで見せる", () => {
    render(
      <Provider>
        <HierarchyListChart clusterList={clusters} argumentList={args} openClusterId="1_1" />
      </Provider>,
    );

    // 全体・1_1・2_1 の 3 グループが開き、1_1 の意見が見える。ほかの 1_2 の枝は閉じたまま
    expect(expandedCount()).toBe(3);
    for (const text of ["意見 A1", "意見 A2", "意見 A3"]) {
      expect(screen.getByText(text)).toBeInTheDocument();
    }
    expect(screen.queryByText("意見 A4")).not.toBeInTheDocument();

    // 押したボタンは消えるので、開いたグループの見出しへフォーカスとスクロールを移す
    const heading = screen.getByText("ラベル 1_1");
    expect(heading).toHaveFocus();
    expect(scrollIntoView).toHaveBeenCalledTimes(1);
    expect(scrollIntoView.mock.contexts[0]).toBe(heading);
  });

  it("検索中に散布図から開いても、検索に一致したほかのグループは開かず、検索語を変えたら従来どおり開く", () => {
    // 検索語 "意見" が 1_1 の A1 と 1_2 の A4 に一致している状態で、1_1 を開いて移ってくる
    const matches = ["A1", "A4"];
    const element = (filteredArgumentIds: string[], textSearch: string) => (
      <Provider>
        <HierarchyListChart
          clusterList={clusters}
          argumentList={args}
          filteredArgumentIds={filteredArgumentIds}
          textSearch={textSearch}
          openClusterId="1_1"
        />
      </Provider>
    );
    const view = render(element(matches, "意見"));

    // 全体・1_1・2_1 だけが開き、検索に一致した A4 の 1_2 の枝は閉じたまま
    expect(expandedCount()).toBe(3);
    expect(screen.getByText("意見 A1")).toBeInTheDocument();
    expect(screen.queryByText("意見 A4")).not.toBeInTheDocument();

    // 同じ検索のまま再描画されても開かない
    view.rerender(element(matches, "意見"));
    expect(screen.queryByText("意見 A4")).not.toBeInTheDocument();

    // 検索語を変えたら、一致したグループを自動で開く
    view.rerender(element(["A4"], "A4"));
    expect(screen.getByText("意見 A4")).toBeInTheDocument();
  });

  it("対立軸ビューから戻るときは、散布図から開いたグループより戻り先を優先する", () => {
    render(
      <Provider>
        <HierarchyListChart
          clusterList={clusters}
          argumentList={args}
          oppositionClusterIds={new Set(["1_2"])}
          onOpenOpposition={jest.fn()}
          reopenClusterId="1_2"
          openClusterId="1_1"
        />
      </Provider>,
    );

    // 1_1 は開かず、戻り先の 1_2 のボタンにだけフォーカスとスクロールが移る
    expect(screen.queryByText("意見 A1")).not.toBeInTheDocument();
    const action = screen.getByRole("button", { name: "この話題の対立を見る" });
    expect(action).toHaveFocus();
    expect(scrollIntoView).toHaveBeenCalledTimes(1);
    expect(scrollIntoView.mock.contexts[0]).toBe(action);
  });
});
