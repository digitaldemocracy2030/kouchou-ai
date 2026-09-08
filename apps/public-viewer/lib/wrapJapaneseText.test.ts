import { wrapJapaneseText } from "./wrapJapaneseText";

it("行頭の句読点と閉じ括弧を避ける", () => {
  expect(wrapJapaneseText("あいう、え", 3)).toBe("あい<br />う、え");
  expect(wrapJapaneseText("あいう）え", 3)).toBe("あい<br />う）え");
});
it("開き括弧を行末に残さない", () => {
  expect(wrapJapaneseText("あい「うえ", 3)).toBe("あい<br />「うえ");
});
it("結合文字・絵文字を分割せず既存改行を保持する", () => {
  expect(wrapJapaneseText("か\u3099👨‍👩‍👧‍👦あ\nい", 1)).toBe("か\u3099<br />👨‍👩‍👧‍👦<br />あ<br />い");
});
it("狭い幅と連続約物でも停止して文字を失わない", () => {
  expect(wrapJapaneseText("（（あ））。", 1).replaceAll("<br />", "")).toBe("（（あ））。");
  expect(wrapJapaneseText("abc", 0)).toBe("a<br />b<br />c");
  expect(wrapJapaneseText("", 3)).toBe("");
});
it("入力に含まれるHTMLをテキストとして表示する", () => {
  expect(wrapJapaneseText("<b>&</b>")).toBe("&lt;b&gt;&amp;&lt;/b&gt;");
});
