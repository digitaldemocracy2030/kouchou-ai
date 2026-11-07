import "@testing-library/jest-dom";
import { Provider } from "@/components/ui/provider";
import type { Argument, Cluster } from "@/type";
import { act, fireEvent, render, screen } from "@testing-library/react";
import { ScatterChart } from "../ScatterChart";

// jsdom には structuredClone が無く、Chakra v3 の recipe 処理が必要とするため補う
globalThis.structuredClone ??= <T,>(value: T): T => (value === undefined ? value : JSON.parse(JSON.stringify(value)));

// Plotly を実描画せず、wheel が「Plotly 側の要素」に届いたかどうかだけ見られる div に差し替える
jest.mock("../ChartCore", () => ({
  ChartCore: () => <div data-testid="plot" />,
}));

// lucide-react は ESM のみ配布のため空コンポーネントに差し替える
jest.mock("lucide-react", () => new Proxy({}, { get: (_, name) => (name === "__esModule" ? true : () => null) }));

const clusters: Cluster[] = [
  { id: "c1", level: 1, label: "cluster-c1", takeaway: "", value: 1, parent: "", density_rank_percentile: 0.1 },
];
const args: Argument[] = [{ arg_id: "a1", argument: "arg-a1", comment_id: 0, x: 0, y: 0, p: 0, cluster_ids: ["c1"] }];

// ホイールが止まってから拡大縮小に切り替わるまでの待ち時間（ScatterChart.tsx の WHEEL_ZOOM_UNLOCK_DELAY_MS）
const UNLOCK_DELAY_MS = 600;

function renderChart(props: Partial<React.ComponentProps<typeof ScatterChart>> = {}) {
  render(
    <Provider>
      <ScatterChart clusterList={clusters} argumentList={args} targetLevel={1} {...props} />
    </Provider>,
  );
  const plot = screen.getByTestId("plot");
  // Plotly が dragger 要素に付ける wheel リスナーの代わり。ここに届けば Plotly が拡大縮小する
  const plotlyWheel = jest.fn();
  plot.addEventListener("wheel", plotlyWheel);
  return {
    plot,
    plotlyWheel,
    wrapper: plot.parentElement as HTMLElement,
    guard: () => screen.queryByTestId("scatter-wheel-guard"),
  };
}

describe("ScatterChart のホイール拡大縮小ガード (#493)", () => {
  beforeEach(() => {
    jest.useFakeTimers();
  });
  afterEach(() => {
    jest.useRealTimers();
  });

  it("何もしていない間はオーバーレイを出さない", () => {
    const { guard } = renderChart();
    expect(guard()).toHaveAttribute("data-visible", "false");
  });

  it("最初のホイールは Plotly に渡さず、オーバーレイを出す（ページスクロールはそのまま通る）", () => {
    const { plot, plotlyWheel, guard } = renderChart();
    const event = fireEvent.wheel(plot, { deltaY: 100 });

    expect(plotlyWheel).not.toHaveBeenCalled();
    // preventDefault はしない（ページのスクロールを止めない）
    expect(event).toBe(true);
    expect(guard()).toHaveAttribute("data-visible", "true");
    expect(screen.getByText("スクロール中は拡大・縮小しません（止めると有効になります）")).toBeInTheDocument();
  });

  it("ホイールが続く間はロックを延長し、止まって 600ms 経つと解除されて Plotly にホイールが届く", () => {
    const { plot, plotlyWheel, guard } = renderChart();
    fireEvent.wheel(plot, { deltaY: 100 });

    act(() => {
      jest.advanceTimersByTime(UNLOCK_DELAY_MS - 1);
    });
    // 解除直前にまたホイールが来たら、待ち時間を数え直す
    fireEvent.wheel(plot, { deltaY: 100 });
    expect(plotlyWheel).not.toHaveBeenCalled();
    act(() => {
      jest.advanceTimersByTime(UNLOCK_DELAY_MS - 1);
    });
    expect(guard()).toHaveAttribute("data-visible", "true");

    act(() => {
      jest.advanceTimersByTime(1);
    });
    expect(guard()).toHaveAttribute("data-visible", "false");

    fireEvent.wheel(plot, { deltaY: -100 });
    expect(plotlyWheel).toHaveBeenCalledTimes(1);
    // 解除後はオーバーレイを出し直さない
    expect(guard()).toHaveAttribute("data-visible", "false");
  });

  it("ポインタが図から出ると再びロックされる", () => {
    const { plot, plotlyWheel, wrapper, guard } = renderChart();
    fireEvent.wheel(plot, { deltaY: 100 });
    act(() => {
      jest.advanceTimersByTime(UNLOCK_DELAY_MS);
    });
    fireEvent.wheel(plot, { deltaY: 100 });
    expect(plotlyWheel).toHaveBeenCalledTimes(1);

    fireEvent.mouseLeave(wrapper);

    fireEvent.wheel(plot, { deltaY: 100 });
    expect(plotlyWheel).toHaveBeenCalledTimes(1);
    expect(guard()).toHaveAttribute("data-visible", "true");
  });

  it("解除待ちの途中でポインタが出たら、待ち時間が過ぎてもロックのまま", () => {
    const { plot, plotlyWheel, wrapper, guard } = renderChart();
    fireEvent.wheel(plot, { deltaY: 100 });
    fireEvent.mouseLeave(wrapper);
    expect(guard()).toHaveAttribute("data-visible", "false");

    act(() => {
      jest.advanceTimersByTime(UNLOCK_DELAY_MS * 2);
    });
    fireEvent.wheel(plot, { deltaY: 100 });
    expect(plotlyWheel).not.toHaveBeenCalled();
  });

  it("ctrl 付きのホイール（トラックパッドのピンチ）はロック中でも Plotly に届く", () => {
    const { plot, plotlyWheel, guard } = renderChart();
    fireEvent.wheel(plot, { deltaY: 10, ctrlKey: true });

    expect(plotlyWheel).toHaveBeenCalledTimes(1);
    expect(guard()).toHaveAttribute("data-visible", "false");
  });

  it("全画面表示ではガードせず、最初からホイールが Plotly に届く", () => {
    const { plot, plotlyWheel, guard } = renderChart({ isFullscreen: true });
    expect(guard()).toBeNull();

    fireEvent.wheel(plot, { deltaY: 100 });
    expect(plotlyWheel).toHaveBeenCalledTimes(1);
  });
});
