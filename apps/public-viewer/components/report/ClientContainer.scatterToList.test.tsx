import "@testing-library/jest-dom";
import { Provider } from "@/components/ui/provider";
import type { Result } from "@/type";
import { act, fireEvent, render, screen, within } from "@testing-library/react";
import fixture from "../dev/viewer-fixture.json";
import { ClientContainer } from "./ClientContainer";

// 散布図（全体）で選んだグループの説明から、階層リストでそのグループの意見を開く（#1207）

// jsdom には structuredClone が無く、Chakra v3 の recipe 処理が必要とするため補う
globalThis.structuredClone ??= <T,>(value: T): T => (value === undefined ? value : JSON.parse(JSON.stringify(value)));

// lucide-react は ESM のみ配布で Jest が変換しないため、全アイコンを空コンポーネントにする
jest.mock("lucide-react", () => new Proxy({}, { get: (_, name) => (name === "__esModule" ? true : () => null) }));

// Plotly を読み込まず、散布図の点クリック（onSelectCluster）をボタンで擬似的に発火させる。階層リストは実物を使う
jest.mock("@/components/charts/ScatterChart", () => ({
  ScatterChart: (props: { targetLevel: number; onSelectCluster?: (id: string) => void }) => (
    <div data-testid="scatter" data-level={props.targetLevel}>
      <button type="button" onClick={() => props.onSelectCluster?.("1_1")}>
        クラスタ1_1を選択
      </button>
    </div>
  ),
}));
jest.mock("@/components/charts/TreemapChart", () => ({ TreemapChart: () => <div data-testid="treemap" /> }));
jest.mock("@/components/icons/ViewIcons", () => ({
  AllViewIcon: () => null,
  DenseViewIcon: () => null,
  DetailViewIcon: () => null,
  HierarchyViewIcon: () => null,
  ListViewIcon: () => null,
}));

const GROUP = "社会的影響に配慮した法案の検討と未来のルール形成";
const SHOW_IN_LIST = "このグループの意見をリストで見る";
const OPPOSITION_GROUP = "AIの権利認識と倫理的共存に向けた社会的枠組みの構築";

function mockWidth(narrow: boolean) {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: (query: string) => ({
      matches: narrow && query.includes("max-width"),
      media: query,
      onchange: null,
      addListener: jest.fn(),
      removeListener: jest.fn(),
      addEventListener: jest.fn(),
      removeEventListener: jest.fn(),
      dispatchEvent: jest.fn(),
    }),
  });
}

beforeAll(() => {
  class ResizeObserverStub {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  Object.defineProperty(window, "ResizeObserver", { writable: true, value: ResizeObserverStub });
  // jsdom は scrollIntoView を実装しないため stub する（連動時にスクロールを呼ぶ）
  Element.prototype.scrollIntoView = jest.fn();
});

async function flush() {
  await act(async () => {
    await new Promise((resolve) => setTimeout(resolve, 50));
  });
}

async function renderViewer() {
  const result = structuredClone(fixture) as unknown as Result;
  render(
    <Provider>
      <ClientContainer result={result} />
    </Provider>,
  );
  await flush();
}

it.each([
  ["PC 幅", false],
  ["スマートフォン幅", true],
])("%s: 散布図で選んだグループから、リスト表示に切り替えてそのグループの意見を開く", async (_, narrow) => {
  mockWidth(narrow);
  await renderViewer();
  // 狭い画面の初期表示はリストなので、散布図（全体）に切り替えてから操作する
  if (narrow) {
    fireEvent.click(screen.getByRole("radio", { name: "全体" }));
    await flush();
  }
  expect(screen.getByTestId("scatter")).toHaveAttribute("data-level", "1");

  // 選ぶ前は、どのグループの説明にもボタンを出さない
  expect(screen.queryByRole("button", { name: SHOW_IN_LIST })).not.toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "クラスタ1_1を選択" }));
  // 選んだグループの説明にだけ出る
  expect(screen.getAllByRole("button", { name: SHOW_IN_LIST })).toHaveLength(1);

  fireEvent.click(screen.getByRole("button", { name: SHOW_IN_LIST }));
  await flush();

  // リスト表示に切り替わり、そのグループの意見が開いている
  expect(screen.getByRole("radio", { name: "リスト" })).toBeChecked();
  expect(screen.queryByTestId("scatter")).not.toBeInTheDocument();
  expect(screen.getByText(GROUP)).toHaveFocus();
  for (const text of [
    "この法案についてはよくわからない部分が多",
    "どちらが正しいのか判断できない",
    "賛成とも反対とも言えない",
  ]) {
    expect(screen.getByText((content) => content.startsWith(text))).toBeInTheDocument();
  }
  // ほかのグループ（1_2）は閉じたまま
  expect(screen.queryByText("AIと人権: 技術革新と倫理の両立に向けた挑戦")).not.toBeInTheDocument();
});

it("リストで開いた後に対立軸ビューへ行って戻っても、散布図から開いたグループを開き直さない", async () => {
  mockWidth(false);
  const result = structuredClone(fixture) as unknown as Result;
  const axis = { id: "axis-1_2", name: "比較する論点", left_pole: "左", right_pole: "右", scores: {} };
  render(
    <Provider>
      <ClientContainer result={{ ...result, opposition_axes: [{ ...axis, cluster_id: "1_2" }] }} />
    </Provider>,
  );
  await flush();

  fireEvent.click(screen.getByRole("button", { name: "クラスタ1_1を選択" }));
  fireEvent.click(screen.getByRole("button", { name: SHOW_IN_LIST }));
  await flush();
  expect(screen.getByText(GROUP)).toHaveFocus();

  // リストで 1_1 を閉じ、1_2 を開いて、その対立を見る
  const rowOf = (label: string) => screen.getByText(label).parentElement?.parentElement as HTMLElement;
  fireEvent.click(within(rowOf(GROUP)).getByRole("button", { name: "折りたたむ" }));
  fireEvent.click(within(rowOf(OPPOSITION_GROUP)).getByRole("button", { name: "展開する" }));
  fireEvent.click(within(rowOf(OPPOSITION_GROUP)).getByRole("button", { name: "この話題の対立を見る" }));
  expect(screen.getByRole("radio", { name: "対立" })).toBeChecked();

  const scrollIntoView = Element.prototype.scrollIntoView as jest.Mock;
  scrollIntoView.mockClear();
  fireEvent.click(screen.getByRole("button", { name: "選んだ話題に戻る" }));
  await flush();

  // 戻り先は 1_2 の「この話題の対立を見る」。1_1 は閉じたままで、そこへスクロールもしない
  expect(screen.getByRole("radio", { name: "リスト" })).toBeChecked();
  expect(within(rowOf(OPPOSITION_GROUP)).getByRole("button", { name: "この話題の対立を見る" })).toHaveFocus();
  expect(scrollIntoView).toHaveBeenCalledTimes(1);
  expect(screen.queryByText((content) => content.startsWith("賛成とも反対とも言えない"))).not.toBeInTheDocument();
});

it("リストで開いた後に全画面表示を出入りしても、散布図から開いたグループを開き直さない", async () => {
  mockWidth(false);
  await renderViewer();
  fireEvent.click(screen.getByRole("button", { name: "クラスタ1_1を選択" }));
  fireEvent.click(screen.getByRole("button", { name: SHOW_IN_LIST }));
  await flush();
  const opinion = (content: string) => content.startsWith("賛成とも反対とも言えない");
  expect(screen.getByText(opinion)).toBeInTheDocument();

  // 全画面のリストはマウントし直されるが、1_1 を最下層まで開き直さない
  fireEvent.click(screen.getByRole("button", { name: "全画面表示" }));
  const dialog = await screen.findByRole("dialog");
  await flush();
  expect(within(dialog).queryByText(opinion)).not.toBeInTheDocument();

  fireEvent.click(within(dialog).getByRole("button", { name: "全画面終了" }));
  await flush();
  expect(screen.queryByText(opinion)).not.toBeInTheDocument();
});
