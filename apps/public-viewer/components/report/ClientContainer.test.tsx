import "@testing-library/jest-dom";
import { Provider } from "@/components/ui/provider";
import type { Result } from "@/type";
import { act, fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import fixture from "../dev/viewer-fixture.json";
import { ClientContainer } from "./ClientContainer";

// jsdom には structuredClone が無く、Chakra v3 の recipe 処理が必要とするため補う
globalThis.structuredClone ??= <T,>(value: T): T => (value === undefined ? value : JSON.parse(JSON.stringify(value)));

// lucide-react は ESM のみ配布で Jest が変換しないため、全アイコンを空コンポーネントにする
jest.mock("lucide-react", () => new Proxy({}, { get: (_, name) => (name === "__esModule" ? true : () => null) }));

// Plotly を読み込まず、散布図に渡された階層とラベル設定を記録する
jest.mock("@/components/charts/ScatterChart", () => ({
  ScatterChart: ({ targetLevel, showClusterLabels }: { targetLevel: number; showClusterLabels: boolean }) => (
    <div data-testid="scatter" data-level={targetLevel} data-show-labels={String(showClusterLabels)} />
  ),
}));
jest.mock("@/components/charts/TreemapChart", () => ({
  TreemapChart: (props: {
    level: string;
    clusterList: Result["clusters"];
    argumentList: Result["arguments"];
    filteredArgumentIds?: string[];
  }) => (
    <div
      data-testid="treemap"
      data-level={props.level}
      data-clusters={props.clusterList.map(({ id }) => id).join(",")}
      data-opinions={props.argumentList.map(({ arg_id }) => arg_id).join(",")}
      data-filtered-opinions={props.filteredArgumentIds?.join(",")}
    />
  ),
}));
jest.mock("@/components/charts/HierarchyListChart", () => ({
  HierarchyListChart: (props: { clusterList: Result["clusters"]; filteredArgumentIds?: string[] }) => (
    <div
      data-testid="hierarchy-list"
      data-clusters={props.clusterList.map(({ id }) => id).join(",")}
      data-filtered-opinions={props.filteredArgumentIds?.join(",")}
    />
  ),
}));
jest.mock("@/components/icons/ViewIcons", () => ({
  AllViewIcon: () => null,
  DenseViewIcon: () => null,
  DetailViewIcon: () => null,
  HierarchyViewIcon: () => null,
  ListViewIcon: () => null,
}));

beforeAll(() => {
  // Chakra の Dialog（zag.js）は ResizeObserver を要求する（jsdom には無い）
  class ResizeObserverStub {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  Object.defineProperty(window, "ResizeObserver", { writable: true, value: ResizeObserverStub });
  // ClientContainer は狭い画面の判定に matchMedia を使う（jsdom には無い）
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: (query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: jest.fn(),
      removeListener: jest.fn(),
      addEventListener: jest.fn(),
      removeEventListener: jest.fn(),
      dispatchEvent: jest.fn(),
    }),
  });
  Element.prototype.scrollIntoView = jest.fn();
});

/**
 * zag.js（SegmentGroup / Dialog）が requestAnimationFrame 後に行う状態更新と
 * dismiss 層の登録・解除を act 内で流す（jsdom の rAF は約16ms後に発火する）
 */
async function flush() {
  await act(async () => {
    await new Promise((resolve) => setTimeout(resolve, 50));
  });
}

async function renderViewer(overrides: Partial<Result> = {}) {
  const result = { ...(structuredClone(fixture) as unknown as Result), ...overrides };
  const utils = render(
    <Provider>
      <ClientContainer result={result} />
    </Provider>,
  );
  await flush();
  return utils;
}

describe("散布図の意見グループ名の初期表示", () => {
  afterEach(() => jest.restoreAllMocks());

  it.each([
    { narrow: true, configured: undefined, expected: false },
    { narrow: false, configured: undefined, expected: true },
    { narrow: true, configured: true, expected: true },
    { narrow: false, configured: false, expected: false },
  ])("画面幅とレポート設定を反映する ($narrow, $configured)", async ({ narrow, configured, expected }) => {
    const matchMedia = window.matchMedia;
    jest.spyOn(window, "matchMedia").mockImplementation((query) => ({
      ...matchMedia(query),
      matches: query === "(max-width: 600px)" && narrow,
    }));
    await renderViewer({
      visualizationConfig: {
        version: "1",
        enabledCharts: ["scatterAll"],
        defaultChart: "scatterAll",
        params: { showClusterLabels: configured },
      },
    });

    expect(screen.getByTestId("scatter")).toHaveAttribute("data-show-labels", String(expected));
  });
});

describe("全画面表示でのクラスタ粒度の切替", () => {
  it("全画面のまま大きいクラスタと細かいクラスタを行き来し、全画面終了も使える", async () => {
    await renderViewer();
    const deepest = Math.max(...fixture.clusters.map((c) => c.level));
    expect(screen.getByTestId("scatter")).toHaveAttribute("data-level", "1");

    fireEvent.click(screen.getByRole("button", { name: "全画面表示" }));
    const dialog = screen.getByRole("dialog");
    expect(within(dialog).getByTestId("scatter")).toHaveAttribute("data-level", "1");

    // 細かいクラスタへ
    fireEvent.click(within(dialog).getByRole("button", { name: "詳細クラスタ" }));
    expect(screen.getByRole("dialog")).toBe(dialog); // 全画面のまま
    expect(within(dialog).getByTestId("scatter")).toHaveAttribute("data-level", String(deepest));
    expect(within(dialog).getByRole("button", { name: "詳細クラスタ" })).toHaveAttribute("aria-pressed", "true");

    // 大きいクラスタへ戻す
    fireEvent.click(within(dialog).getByRole("button", { name: "全体" }));
    expect(screen.getByRole("dialog")).toBe(dialog);
    expect(within(dialog).getByTestId("scatter")).toHaveAttribute("data-level", "1");

    // 全画面終了は従来どおり動く
    fireEvent.click(within(dialog).getByRole("button", { name: "全画面終了" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    // 全画面を抜けた後も、通常表示は全画面中に選んだ粒度を引き継ぐ
    expect(screen.getByTestId("scatter")).toHaveAttribute("data-level", "1");
    await flush();
  });

  it("全画面中に切り替えた粒度は、全画面を抜けた後の通常表示にも反映される", async () => {
    await renderViewer();
    const deepest = Math.max(...fixture.clusters.map((c) => c.level));
    fireEvent.click(screen.getByRole("button", { name: "全画面表示" }));
    const dialog = screen.getByRole("dialog");
    fireEvent.click(within(dialog).getByRole("button", { name: "詳細クラスタ" }));
    fireEvent.click(within(dialog).getByRole("button", { name: "全画面終了" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(screen.getByTestId("scatter")).toHaveAttribute("data-level", String(deepest));
    await flush();
  });

  it("Escape キーで全画面を終了できる", async () => {
    await renderViewer();
    fireEvent.click(screen.getByRole("button", { name: "全画面表示" }));
    await screen.findByRole("dialog");
    // zag.js の dismiss 層は開いた後に rAF で document へ keydown を登録する
    await flush();
    fireEvent.keyDown(document, { key: "Escape" });
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());
    await flush();
  });
});

describe("濃い意見の抽出結果が 0 件のとき", () => {
  it("一つ上の階層を濃い意見として表示せず、全体表示へ戻す", async () => {
    await renderViewer({
      visualizationConfig: {
        defaultChart: "scatterDensity",
        // どのクラスタも条件を満たさない最小件数
        params: { scatterDensity: { maxDensity: 1, minValue: 1_000_000 } },
      },
    } as Partial<Result>);

    expect(screen.getByRole("radio", { name: "全体" })).toBeChecked();
    expect(screen.getByRole("radio", { name: "濃い意見" })).not.toBeChecked();
    expect(screen.getByTestId("scatter")).toHaveAttribute("data-level", "1");
    await flush();
  });

  it("管理者が「全体」を外していれば、有効な表示の中から選び直す", async () => {
    await renderViewer({
      visualizationConfig: {
        enabledCharts: ["scatterDensity", "treemap"],
        defaultChart: "scatterDensity",
        params: { scatterDensity: { maxDensity: 1, minValue: 1_000_000 } },
      },
    } as Partial<Result>);

    expect(screen.queryByRole("radio", { name: "全体" })).not.toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "階層" })).toBeChecked();
    expect(screen.getByRole("radio", { name: "濃い意見" })).not.toBeChecked();
    expect(screen.getByTestId("treemap")).toBeInTheDocument();
    expect(screen.queryByTestId("scatter")).not.toBeInTheDocument();
    await flush();
  });

  it("「全体」が無いときは、表示順で先頭の選べる表示へ戻す", async () => {
    await renderViewer({
      visualizationConfig: {
        enabledCharts: ["scatterDensity", "treemap", "hierarchyList"],
        chartOrder: ["scatterDensity", "hierarchyList", "treemap"],
        defaultChart: "scatterDensity",
        params: { scatterDensity: { maxDensity: 1, minValue: 1_000_000 } },
      },
    } as Partial<Result>);

    expect(screen.getByRole("radio", { name: "リスト" })).toBeChecked();
    expect(screen.getByTestId("hierarchy-list")).toBeInTheDocument();
    await flush();
  });

  it("他に利用できる表示が無ければ案内を表示し、外されたチャートは描画しない", async () => {
    await renderViewer({
      visualizationConfig: {
        version: "1",
        enabledCharts: ["scatterDensity"],
        defaultChart: "scatterDensity",
        params: { scatterDensity: { maxDensity: 1, minValue: 1_000_000 } },
      },
    });

    expect(screen.queryByRole("radio", { name: "全体" })).not.toBeInTheDocument();
    expect(screen.getByRole("radio", { name: "濃い意見" })).not.toBeChecked();
    expect(screen.getByRole("status")).toHaveTextContent("このレポートで利用できる表示はありません。");
    expect(screen.queryByTestId("scatter")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "全画面表示" })).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "フィルタ" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "表示設定" }));
    expect(await screen.findByRole("dialog")).toBeInTheDocument();
    await flush();
  });
});

describe("保存済み設定と利用できる表示の不一致", () => {
  it.each(["removedMode", "scatterAll", "scatterDetail"])(
    "指定された初期表示 %s を描けない場合、表示順で有効なモードを使う",
    async (defaultChart) => {
      const result = fixture as unknown as Result;
      await renderViewer({
        clusters: result.clusters.filter((cluster) => cluster.level <= 1),
        visualizationConfig: {
          version: "1",
          enabledCharts: ["removedMode", "scatterDetail", "hierarchyList", "treemap"],
          chartOrder: ["treemap", "hierarchyList", "scatterDetail"],
          defaultChart,
        },
      });
      expect(screen.getByRole("radio", { name: "階層" })).toBeChecked();
      expect(screen.getByTestId("treemap")).toBeInTheDocument();
      expect(screen.queryByTestId("scatter")).not.toBeInTheDocument();
    },
  );

  it("明示的に空のリストを保存したレポートで、既定の表示を勝手に有効にしない", async () => {
    await renderViewer({ visualizationConfig: { version: "1", enabledCharts: [] } });
    expect(screen.getByRole("status")).toHaveTextContent("このレポートで利用できる表示はありません。");
    expect(screen.queryByRole("radio")).not.toBeInTheDocument();
    expect(screen.queryByTestId("scatter")).not.toBeInTheDocument();
  });
});

describe("図の上の意見検索", () => {
  it("散布図からキーワードを検索し、一致する意見をリストに渡す", async () => {
    const args = (structuredClone(fixture) as unknown as Result).arguments;
    args[0].argument = "避難時にエレベーターを使えるか知りたい";
    await renderViewer({ arguments: args });
    expect(screen.getByTestId("scatter")).toBeInTheDocument();
    const search = screen.getByRole("searchbox", { name: "抽出された意見を検索" });
    fireEvent.change(search, { target: { value: " エレベーター " } });
    fireEvent.click(screen.getByRole("button", { name: "検索" }));
    expect(screen.getByText("「エレベーター」に一致する意見：1件")).toBeVisible();
    expect(screen.getByTestId("hierarchy-list")).toHaveAttribute("data-filtered-opinions", args[0].arg_id);
    fireEvent.click(screen.getByRole("button", { name: "検索を解除" }));
    expect(search).toHaveValue("");
    expect(search).toHaveFocus();
    expect(screen.getByTestId("hierarchy-list")).not.toHaveAttribute("data-filtered-opinions");
  });

  it("リストを使わないレポートでも現在の表示で検索でき、0件からやり直せる", async () => {
    await renderViewer({ visualizationConfig: { version: "1", enabledCharts: ["scatterAll"] } });
    const search = screen.getByRole("searchbox");
    fireEvent.change(search, { target: { value: "該当しない語" } });
    fireEvent.click(screen.getByRole("button", { name: "検索" }));
    expect(screen.getByText("「該当しない語」に一致する意見：0件")).toBeVisible();
    expect(screen.getByTestId("scatter")).toBeInTheDocument();
    fireEvent.change(search, { target: { value: "より良い社会" } });
    fireEvent.click(screen.getByRole("button", { name: "検索" }));
    expect(screen.getByText("「より良い社会」に一致する意見：1件")).toBeVisible();
  });
});

describe("フィルタボタン", () => {
  it("属性のあるレポートではフィルタボタンからテキスト検索に到達できる", async () => {
    await renderViewer();
    fireEvent.click(screen.getByRole("button", { name: "フィルタ" }));
    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByText("テキスト検索")).toBeInTheDocument();
    await flush();
  });

  it("属性の無いレポート（attributes=null）でも、フィルタボタンからテキスト検索を使える", async () => {
    // 属性列を選ばずに作ったレポートでは analysis-core が attributes: null を出力する
    const args = (structuredClone(fixture) as unknown as Result).arguments.map((a) => ({
      ...a,
      attributes: null,
    })) as unknown as Result["arguments"];
    await renderViewer({ arguments: args });

    fireEvent.click(screen.getByRole("button", { name: "フィルタ" }));
    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByText("テキスト検索")).toBeInTheDocument();
    // 属性 0 件の案内は閲覧者向けの文言にする（作成者向けの「CSVファイルをアップロードする際に…」は出さない）
    expect(within(dialog).getByText("このレポートには、絞り込みに使える属性情報がありません。")).toBeInTheDocument();
    expect(within(dialog).queryByText(/CSVファイルをアップロード/)).not.toBeInTheDocument();

    fireEvent.change(within(dialog).getByRole("textbox"), { target: { value: "AI" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "設定を適用" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());

    // 検索中であることがバッジ（有効なフィルタ数）でわかる
    expect(screen.getByRole("searchbox")).toHaveValue("AI");
    expect(within(screen.getByRole("button", { name: "フィルタ" })).getByText("1")).toBeInTheDocument();
    await flush();
  });
});

describe("対立軸ビュー", () => {
  it("対立軸データがないレポートに導線を出さない", async () => {
    await renderViewer();
    expect(screen.queryByRole("radio", { name: "対立" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "この話題の対立を見る" })).not.toBeInTheDocument();
  });

  it("選んだ話題と対立軸を全画面表示の往復で保持する", async () => {
    const result = fixture as unknown as Result;
    const [firstTopic, secondTopic] = result.clusters.filter((cluster) => cluster.level === 1);
    const axis = { left_pole: "左", right_pole: "右", scores: {} };
    await renderViewer({
      opposition_axes: [
        { ...axis, id: "first-axis", name: "第一の論点", cluster_id: firstTopic.id },
        { ...axis, id: "second-axis", name: "第二の論点", cluster_id: secondTopic.id },
        { ...axis, id: "third-axis", name: "第三の論点", cluster_id: secondTopic.id },
      ],
    });

    fireEvent.click(screen.getByRole("radio", { name: "対立" }));
    fireEvent.change(screen.getByRole("combobox", { name: "話題" }), { target: { value: secondTopic.id } });
    fireEvent.change(screen.getByRole("combobox", { name: "対立軸" }), { target: { value: "third-axis" } });
    fireEvent.click(screen.getByRole("button", { name: "全画面表示" }));

    const dialog = await screen.findByRole("dialog");
    expect(within(dialog).getByRole("combobox", { name: "話題" })).toHaveValue(secondTopic.id);
    expect(within(dialog).getByRole("combobox", { name: "対立軸" })).toHaveValue("third-axis");

    fireEvent.click(within(dialog).getByRole("button", { name: "全画面終了" }));
    expect(screen.getByRole("combobox", { name: "話題" })).toHaveValue(secondTopic.id);
    expect(screen.getByRole("combobox", { name: "対立軸" })).toHaveValue("third-axis");
    await flush();
  });

  it("クラスタの導線から、該当する軸・意見・採点の内訳を表示する", async () => {
    const result = fixture as unknown as Result;
    const topic = result.clusters.find((cluster) => cluster.level === 1);
    if (!topic) throw new Error("Fixture must have a topic");
    const opinions = result.arguments.filter((arg) => arg.cluster_ids.includes(topic.id));
    const [left, right, notApplicable] = opinions;
    await renderViewer({
      arguments: [...result.arguments, { ...notApplicable, arg_id: "unscored-opinion", argument: "未採点の意見" }],
      opposition_axes: [
        {
          id: "test-axis",
          cluster_id: topic.id,
          name: "比較する論点",
          left_pole: "左の主張",
          right_pole: "右の主張",
          scores: { [left.arg_id]: 1, [right.arg_id]: 6, [notApplicable.arg_id]: null },
        },
      ],
    });

    fireEvent.click(screen.getByRole("button", { name: "この話題の対立を見る" }));
    expect(screen.getByRole("radio", { name: "対立" })).toBeChecked();
    expect(screen.getByRole("heading", { name: "比較する論点" })).toBeInTheDocument();
    expect(screen.getByRole("combobox", { name: "対立軸" })).toHaveValue("test-axis");
    expect(screen.getByText("左の主張")).toBeInTheDocument();
    expect(screen.getByText(right.argument)).toBeInTheDocument();
    expect(screen.getByText(/該当なし 1件/)).toBeInTheDocument();
    expect(screen.getByText(new RegExp(`未採点 ${(opinions.length - 2).toLocaleString()}件`))).toBeInTheDocument();
    expect(screen.queryByText(notApplicable.argument)).not.toBeInTheDocument();
    await flush();
  });
});

describe("階層図の密度フィルター", () => {
  const result = {
    clusters: [
      { id: "0", parent: "", level: 0, label: "全意見のグループ", value: 4, density_rank_percentile: 0 },
      { id: "1_0", parent: "0", level: 1, label: "教育", value: 1, density_rank_percentile: 0.8 },
      { id: "1_1", parent: "0", level: 1, label: "交通", value: 3, density_rank_percentile: 0.8 },
      { id: "2_0", parent: "1_0", level: 2, label: "図書館", value: 1, density_rank_percentile: 0.1 },
      { id: "2_1", parent: "1_1", level: 2, label: "料金", value: 2, density_rank_percentile: 0.2 },
      { id: "2_2", parent: "1_1", level: 2, label: "自転車", value: 1, density_rank_percentile: 0.9 },
    ].map((cluster) => ({ ...cluster, takeaway: "" })),
    arguments: [
      { arg_id: "a", argument: "図書館を増やす", cluster_ids: ["0", "1_0", "2_0"] },
      { arg_id: "b", argument: "自治体の料金", cluster_ids: ["0", "1_1", "2_1"] },
      { arg_id: "c", argument: "運賃の見直し", cluster_ids: ["0", "1_1", "2_1"] },
      { arg_id: "d", argument: "自治体の自転車施策", cluster_ids: ["0", "1_1", "2_2"] },
    ].map((opinion) => ({ ...opinion, comment_id: 0, x: 0, y: 0, p: 0 })),
    visualizationConfig: {
      version: "1.0",
      enabledCharts: ["scatterAll", "scatterDetail", "scatterDensity", "treemap", "hierarchyList"],
      defaultChart: "treemap",
      params: { scatterDensity: { maxDensity: 0.2, minValue: 2 } },
    },
  } satisfies Partial<Result>;
  const switchName = "濃い意見グループに絞る";

  it("既定はオフで、オンにすると残る親へ戻り、図と説明が同じグループを表示する", async () => {
    await renderViewer(result);
    const toggle = screen.getByRole("switch", { name: switchName });
    const details = screen.getByRole("region", { name: "階層図の説明" });
    expect(toggle).not.toBeChecked();
    expect(screen.getByTestId("treemap")).toHaveAttribute("data-clusters", "0,1_0,1_1,2_0,2_1,2_2");

    fireEvent.click(within(details).getByRole("button", { name: "交通" }));
    fireEvent.click(within(details).getByRole("button", { name: "自転車" }));
    expect(screen.getByTestId("treemap")).toHaveAttribute("data-level", "2_2");
    fireEvent.click(toggle);

    await waitFor(() => expect(screen.getByTestId("treemap")).toHaveAttribute("data-level", "1_1"));
    expect(screen.getByTestId("treemap")).toHaveAttribute("data-clusters", "0,1_1,2_1");
    expect(screen.getByTestId("treemap")).toHaveAttribute("data-opinions", "b,c");
    expect(within(details).getByRole("heading", { name: "表示中: 交通" })).toBeInTheDocument();
    expect(within(details).getByRole("button", { name: "料金" })).toBeInTheDocument();
    expect(within(details).queryByRole("button", { name: "自転車" })).not.toBeInTheDocument();
    expect(within(details).getAllByText("意見 2件（フィルター後の全意見に対する割合: 100.00%）")).toHaveLength(2);

    fireEvent.click(toggle);
    expect(await within(details).findByRole("button", { name: "自転車" })).toBeInTheDocument();

    fireEvent.click(toggle);
    await waitFor(() => expect(screen.getByTestId("treemap")).toHaveAttribute("data-opinions", "b,c"));
    fireEvent.click(screen.getByRole("radio", { name: "リスト" }));
    expect(screen.queryByRole("switch", { name: switchName })).not.toBeInTheDocument();
    expect(screen.getByTestId("hierarchy-list")).toHaveAttribute("data-clusters", "0,1_0,1_1,2_0,2_1,2_2");
    expect(screen.getByTestId("hierarchy-list")).not.toHaveAttribute("data-filtered-opinions");
    await flush();
  });

  it("テキスト検索と密度条件を同時に満たす意見だけを図と説明に反映する", async () => {
    await renderViewer(result);
    fireEvent.click(screen.getByRole("switch", { name: switchName }));
    fireEvent.click(screen.getByRole("button", { name: "フィルタ" }));
    const dialog = await screen.findByRole("dialog");
    fireEvent.change(within(dialog).getByRole("textbox"), { target: { value: "自治体" } });
    fireEvent.click(within(dialog).getByRole("button", { name: "設定を適用" }));
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument());

    expect(screen.getByTestId("treemap")).toHaveAttribute("data-filtered-opinions", "b");
    expect(screen.getByTestId("treemap")).toHaveAttribute("data-opinions", "b");
    expect(screen.getAllByText("意見 1件（フィルター後の全意見に対する割合: 100.00%）")).toHaveLength(2);
    await flush();
  });

  it("全画面で絞り込みの結果が空でもスイッチが使え、通常表示にも状態を引き継ぐ", async () => {
    await renderViewer({
      ...result,
      visualizationConfig: {
        ...result.visualizationConfig,
        params: { scatterDensity: { maxDensity: 0.1, minValue: 5 } },
      },
    });

    fireEvent.click(screen.getByRole("button", { name: "全画面表示" }));
    const dialog = await screen.findByRole("dialog");
    fireEvent.click(within(dialog).getByRole("switch", { name: switchName }));
    expect(await within(dialog).findByRole("status")).toHaveTextContent("この階層に該当する意見はありません。");
    expect(within(dialog).queryByTestId("treemap")).not.toBeInTheDocument();
    fireEvent.click(within(dialog).getByRole("button", { name: "全画面終了" }));

    const toggle = screen.getByRole("switch", { name: switchName });
    expect(toggle).toBeChecked();
    expect(screen.getByText("意見 0件（フィルター後の全意見に対する割合: —）")).toBeInTheDocument();
    fireEvent.click(toggle);
    expect(await screen.findByTestId("treemap")).toHaveAttribute("data-clusters", "0,1_0,1_1,2_0,2_1,2_2");
    await flush();
  });

  it("最深階層がルートだけのレポートも、密度条件に合わなければ空の結果を表示する", async () => {
    await renderViewer({
      ...result,
      clusters: [{ ...result.clusters[0], value: 1 }],
      arguments: [{ ...result.arguments[0], cluster_ids: ["0"] }],
    });
    fireEvent.click(screen.getByRole("switch", { name: switchName }));
    expect(await screen.findByRole("status")).toHaveTextContent("この階層に該当する意見はありません。");
    expect(screen.getByRole("heading", { name: "表示中: 全意見のグループ" })).toBeInTheDocument();
    expect(screen.getByText("意見 0件（フィルター後の全意見に対する割合: —）")).toBeInTheDocument();
    await flush();
  });
});
