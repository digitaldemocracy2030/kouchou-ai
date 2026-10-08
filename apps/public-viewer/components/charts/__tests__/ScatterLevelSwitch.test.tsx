import "@testing-library/jest-dom";
import { Provider } from "@/components/ui/provider";
import type { Result } from "@/type";
import { fireEvent, render, screen } from "@testing-library/react";
import { ScatterLevelSwitch } from "../ScatterLevelSwitch";

// jsdom には structuredClone が無く、Chakra v3 の recipe 処理が必要とするため補う
globalThis.structuredClone ??= <T,>(value: T): T => (value === undefined ? value : JSON.parse(JSON.stringify(value)));

// lucide-react は ESM のみ配布で Jest が変換しないため、全アイコンを空コンポーネントにする
jest.mock("lucide-react", () => new Proxy({}, { get: (_, name) => (name === "__esModule" ? true : () => null) }));

// Mock icons (SVG のタイトルがボタン名に混ざらないようにする)
jest.mock("@/components/icons/ViewIcons", () => ({
  AllViewIcon: () => null,
  DenseViewIcon: () => null,
  DetailViewIcon: () => null,
  HierarchyViewIcon: () => null,
  ListViewIcon: () => null,
}));

const cluster = (id: string, level: number, parent = "") => ({
  id,
  level,
  label: `cluster-${id}`,
  takeaway: "",
  value: 10,
  parent,
  density_rank_percentile: 0.5,
});

const twoLevelResult = {
  clusters: [cluster("1", 1), cluster("1-1", 2, "1"), cluster("1-2", 2, "1")],
  arguments: [],
  config: { title: "Test" },
} as unknown as Result;

const oneLevelResult = {
  clusters: [cluster("1", 1)],
  arguments: [],
  config: { title: "Test" },
} as unknown as Result;

function renderSwitch(props: Partial<React.ComponentProps<typeof ScatterLevelSwitch>> = {}) {
  const onChange = jest.fn();
  const utils = render(
    <Provider>
      <ScatterLevelSwitch selected="scatterAll" onChange={onChange} result={twoLevelResult} {...props} />
    </Provider>,
  );
  return { onChange, ...utils };
}

describe("ScatterLevelSwitch", () => {
  it("大きいクラスタ（全体）と細かいクラスタ（詳細クラスタ）を切り替えられる", () => {
    const { onChange } = renderSwitch();
    const group = screen.getByRole("group", { name: "クラスタの粒度" });
    expect(group).toBeInTheDocument();

    const all = screen.getByRole("button", { name: "全体" });
    const detail = screen.getByRole("button", { name: "詳細クラスタ" });
    expect(all).toHaveAttribute("aria-pressed", "true");
    expect(detail).toHaveAttribute("aria-pressed", "false");

    fireEvent.click(detail);
    expect(onChange).toHaveBeenCalledWith("scatterDetail");

    // 選択中のボタンを押しても再通知しない
    fireEvent.click(all);
    expect(onChange).toHaveBeenCalledTimes(1);
  });

  it("細かいクラスタ側が選択されているときは「全体」へ戻せる", () => {
    const { onChange } = renderSwitch({ selected: "scatterDetail" });
    expect(screen.getByRole("button", { name: "詳細クラスタ" })).toHaveAttribute("aria-pressed", "true");
    fireEvent.click(screen.getByRole("button", { name: "全体" }));
    expect(onChange).toHaveBeenCalledWith("scatterAll");
  });

  it("濃い意見の切替も表示し、親からの無効化を反映する", () => {
    renderSwitch({ disabledModeOverrides: { scatterDensity: true } });
    const dense = screen.getByRole("button", { name: "濃い意見" });
    expect(dense).toBeDisabled();
    expect(screen.getByRole("button", { name: "詳細クラスタ" })).toBeEnabled();
  });

  it("enabledCharts で許可された散布図モードだけを並べる", () => {
    renderSwitch({
      enabledCharts: ["scatterDetail", "scatterAll", "treemap"],
      chartOrder: ["scatterDetail", "scatterAll"],
    });
    const buttons = screen.getAllByRole("button");
    expect(buttons.map((b) => b.textContent)).toEqual(["詳細クラスタ", "全体"]);
    expect(screen.queryByRole("button", { name: "濃い意見" })).not.toBeInTheDocument();
  });

  it("クラスタが1階層のみなら細かいクラスタ側を無効にする", () => {
    renderSwitch({ result: oneLevelResult });
    expect(screen.getByRole("button", { name: "詳細クラスタ" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "全体" })).toBeEnabled();
  });

  it("散布図以外の表示中や切替先が1つしかないときは何も描画しない", () => {
    const { container, rerender } = renderSwitch({ selected: "treemap" });
    expect(container.querySelector("fieldset")).toBeNull();

    rerender(
      <Provider>
        <ScatterLevelSwitch
          selected="scatterAll"
          onChange={jest.fn()}
          result={twoLevelResult}
          enabledCharts={["scatterAll", "treemap"]}
        />
      </Provider>,
    );
    expect(container.querySelector("fieldset")).toBeNull();
  });
});
