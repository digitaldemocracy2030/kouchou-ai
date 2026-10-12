import "@testing-library/jest-dom";
import { Provider } from "@/components/ui/provider";
import type { Cluster } from "@/type";
import { render, screen } from "@testing-library/react";
import { ClusterOverview } from "./ClusterOverview";

// jsdom には structuredClone が無く、Chakra v3 の recipe 処理が必要とするため補う
globalThis.structuredClone ??= <T,>(value: T): T => (value === undefined ? value : JSON.parse(JSON.stringify(value)));

// lucide-react は ESM のみ配布で Jest が変換しないため、全アイコンを空コンポーネントにする
jest.mock("lucide-react", () => new Proxy({}, { get: (_, name) => (name === "__esModule" ? true : () => null) }));

const cluster: Cluster = {
  level: 1,
  id: "a",
  label: "交通",
  takeaway: "交通の説明",
  value: 10,
  parent: "0",
  density_rank_percentile: 0,
};

function renderOverview(props: Partial<React.ComponentProps<typeof ClusterOverview>>) {
  return render(
    <Provider>
      <ClusterOverview cluster={cluster} {...props} />
    </Provider>,
  );
}

it("フィルター未適用なら元の件数を表示する", () => {
  renderOverview({});
  expect(screen.getByText("10件")).toBeInTheDocument();
});

it("フィルター適用中は渡された件数とフィルター後ラベルを表示する", () => {
  renderOverview({ count: 3, isFiltering: true });
  expect(screen.getByText("3件（フィルター後）")).toBeInTheDocument();
});

it("散布図で選択中のクラスタは aria-current でハイライトし、スクロールする", () => {
  const scrollIntoView = jest.fn();
  Element.prototype.scrollIntoView = scrollIntoView;
  const { container } = renderOverview({ isSelected: true });
  expect(container.querySelector('[aria-current="true"]')).toBeInTheDocument();
  expect(scrollIntoView).toHaveBeenCalled();
});
