import type { Argument } from "@/type";
import { type FilterParams, filterArgumentIds } from "./attributeFilterUtils";

// 空欄の属性の表し方は入力経路で異なる。
// - スプレッドシート取り込み・CLI の CSV: 属性列が全部空欄の回答は attributes=null、一部だけ空欄なら値が null
// - admin の CSV アップロード: 空欄は "" のまま残る
// どの表し方でもフィルタ結果が同じになることを確かめる。
const mk = (id: string, text: string, attributes: Record<string, string | null> | null): Argument =>
  ({
    arg_id: id,
    argument: text,
    comment_id: 0,
    x: 0,
    y: 0,
    p: 0,
    cluster_ids: ["0", "1_0"],
    attributes,
  }) as unknown as Argument;

const args: Argument[] = [
  mk("A1", "子育て支援を増やしてほしい", { age: "25", gender: "女性" }),
  mk("A2", "子育て支援を増やしてほしい", { age: null, gender: "男性" }), // 年齢だけ空欄（null）
  mk("A3", "子育て支援を増やしてほしい", null), // 属性を全部空欄（null）
  mk("A4", "子育て支援を増やしてほしい", { age: "", gender: "" }), // 属性を全部空欄（""）
  mk("A5", "道路を直してほしい", { age: "28", gender: "女性" }),
];

const base: FilterParams = {
  attributeFilters: {},
  numericRanges: {},
  enabledRanges: {},
  includeEmptyValues: {},
  textSearch: "",
};

describe("filterArgumentIds", () => {
  it("フィルタ条件が無ければ undefined（全件表示）", () => {
    expect(filterArgumentIds(args, base)).toBeUndefined();
  });

  it("テキスト検索だけなら、属性の有無にかかわらず本文で判定する", () => {
    expect(filterArgumentIds(args, { ...base, textSearch: "子育て" })).toEqual(["A1", "A2", "A3", "A4"]);
  });

  it('カテゴリ条件だけ: 属性が空（null / ""）の意見は一致しない', () => {
    expect(filterArgumentIds(args, { ...base, attributeFilters: { gender: ["女性"] } })).toEqual(["A1", "A5"]);
  });

  it("カテゴリ条件 + テキスト検索: attributes=null の意見も属性の条件で除外される", () => {
    expect(filterArgumentIds(args, { ...base, attributeFilters: { gender: ["女性"] }, textSearch: "子育て" })).toEqual([
      "A1",
    ]);
  });

  it("数値範囲だけ: 空の値は除外される", () => {
    expect(
      filterArgumentIds(args, { ...base, numericRanges: { age: [20, 30] }, enabledRanges: { age: true } }),
    ).toEqual(["A1", "A5"]);
  });

  it("数値範囲 + テキスト検索: attributes=null の意見も範囲の条件で除外される", () => {
    expect(
      filterArgumentIds(args, {
        ...base,
        numericRanges: { age: [20, 30] },
        enabledRanges: { age: true },
        textSearch: "子育て",
      }),
    ).toEqual(["A1"]);
  });

  it('数値範囲 + 空の値を含める: null・""・attributes=null を同じく空として含める', () => {
    expect(
      filterArgumentIds(args, {
        ...base,
        numericRanges: { age: [20, 30] },
        enabledRanges: { age: true },
        includeEmptyValues: { age: true },
      }),
    ).toEqual(["A1", "A2", "A3", "A4", "A5"]);
  });

  it("数値範囲 + 空の値を含める + テキスト検索", () => {
    expect(
      filterArgumentIds(args, {
        ...base,
        numericRanges: { age: [20, 30] },
        enabledRanges: { age: true },
        includeEmptyValues: { age: true },
        textSearch: "子育て",
      }),
    ).toEqual(["A1", "A2", "A3", "A4"]);
  });
});
