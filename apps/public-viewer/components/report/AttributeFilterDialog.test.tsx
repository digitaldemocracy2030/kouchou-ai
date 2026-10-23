import "@testing-library/jest-dom";
import { Provider } from "@/components/ui/provider";
import { act, fireEvent, render, screen } from "@testing-library/react";
import { AttributeFilterDialog } from "./AttributeFilterDialog";
import type { AttributeMeta, NumericRangeFilters } from "./attributeFilterUtils";

// jsdom には structuredClone が無く、Chakra v3 の recipe 処理が必要とするため補う
globalThis.structuredClone ??= <T,>(value: T): T => (value === undefined ? value : JSON.parse(JSON.stringify(value)));
jest.mock("lucide-react", () => new Proxy({}, { get: (_, name) => (name === "__esModule" ? true : () => null) }));

beforeAll(() => {
  // Chakra の Dialog（zag.js）は ResizeObserver を要求する（jsdom には無い）
  class ResizeObserverStub {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  Object.defineProperty(window, "ResizeObserver", { writable: true, value: ResizeObserverStub });
});

const ageMeta: AttributeMeta = {
  name: "age",
  type: "numeric",
  values: ["19", "45", "77"],
  valueCounts: { "19": 1, "45": 1, "77": 1 },
  numericRange: [19, 77],
};

async function renderDialog(initialNumericRanges: NumericRangeFilters = {}) {
  const onApplyFilters = jest.fn();
  render(
    <Provider>
      <AttributeFilterDialog
        attributes={[ageMeta]}
        initialNumericRanges={initialNumericRanges}
        initialEnabledRanges={{ age: true }}
        onApplyFilters={onApplyFilters}
        onClose={() => {}}
      />
    </Provider>,
  );
  await act(async () => {
    await new Promise((resolve) => setTimeout(resolve, 50));
  });
  const [minInput, maxInput] = screen.getAllByRole("spinbutton") as HTMLInputElement[];
  return { onApplyFilters, minInput, maxInput };
}

function apply() {
  fireEvent.click(screen.getByRole("button", { name: "設定を適用" }));
}

// 欄を全選択してキーボードで 1 文字ずつ打つ操作を再現する。
// 1 文字目は全体を置き換え、2 文字目以降はその時点で欄に表示されている値の末尾に足す
// （jsdom の fireEvent.change は caret を扱えないため、表示値に追記して近似する）。
function typeInto(input: HTMLInputElement, text: string) {
  fireEvent.change(input, { target: { value: text[0] } });
  for (const ch of text.slice(1)) {
    fireEvent.change(input, { target: { value: input.value + ch } });
  }
}

describe("AttributeFilterDialog の数値範囲入力", () => {
  it("入力途中の値を丸めず、そのまま欄に残す", async () => {
    const { minInput, maxInput } = await renderDialog();
    fireEvent.change(maxInput, { target: { value: "5" } }); // 最小値 19 より小さい途中の値
    expect(maxInput.value).toBe("5");
    fireEvent.change(minInput, { target: { value: "" } }); // 空欄も途中状態として許す
    expect(minInput.value).toBe("");
  });

  it("30〜50 を 1 文字ずつ入力すると [30, 50] で適用される", async () => {
    const { minInput, maxInput, onApplyFilters } = await renderDialog();
    typeInto(minInput, "30");
    typeInto(maxInput, "50");
    expect(minInput.value).toBe("30");
    expect(maxInput.value).toBe("50");
    apply();
    expect(onApplyFilters).toHaveBeenCalledTimes(1);
    expect(onApplyFilters.mock.calls[0][1]).toEqual({ age: [30, 50] });
  });

  it("最大値 77 を Backspace で 7 にしてから 70 に直せる", async () => {
    const { maxInput, onApplyFilters } = await renderDialog();
    fireEvent.change(maxInput, { target: { value: maxInput.value.slice(0, -1) } }); // End → Backspace
    fireEvent.change(maxInput, { target: { value: `${maxInput.value}0` } });
    expect(maxInput.value).toBe("70");
    apply();
    expect(onApplyFilters.mock.calls[0][1]).toEqual({ age: [19, 70] });
  });

  it("空欄のまま適用した端は、属性の最小・最大値として扱う（0 にしない）", async () => {
    const { minInput, maxInput, onApplyFilters } = await renderDialog();
    fireEvent.change(minInput, { target: { value: "" } });
    fireEvent.change(maxInput, { target: { value: "" } });
    apply();
    expect(onApplyFilters.mock.calls[0][1]).toEqual({ age: [19, 77] });
  });

  it("最小値が最大値より大きいまま適用したら、両端を入れ替える", async () => {
    const { minInput, maxInput, onApplyFilters } = await renderDialog();
    typeInto(minInput, "60");
    typeInto(maxInput, "30");
    apply();
    expect(onApplyFilters.mock.calls[0][1]).toEqual({ age: [30, 60] });
  });

  it("適用済みの範囲を開き直すと欄に表示される", async () => {
    const { minInput, maxInput } = await renderDialog({ age: [25, 40] });
    expect(minInput.value).toBe("25");
    expect(maxInput.value).toBe("40");
  });
});
