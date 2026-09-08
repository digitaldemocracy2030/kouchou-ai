import * as iconv from "iconv-lite";
import { parseCsv as parse } from "./parseCsv";

describe("CSVの読み込み", () => {
  it.each([
    ['comment-body,age\n"unclosed,20', "引用符"],
    ["comment-body,age\na,20,extra", "列が多"],
    ["comment-body,age\na", "列が少"],
    ["comment-body,comment-body\na,b", "同じ名前"],
    ["comment-body,\na,b", "名前のない列"],
    ["comment-body,age", "データがありません"],
  ])("壊れたCSVを理由付きで拒否: %s", async (csv, reason) => {
    await expect(parse(new File([csv], "test.csv", { type: "text/csv" }))).rejects.toThrow(reason);
  });

  it.each([
    "comment-body\nfirst opinion\nsecond opinion",
    '\ufeffcomment-body,age\n"comma, and ""quotes""",20',
    'comment-body,age\r\n"multiple\nlines",20\r\nnext,30',
  ])("正常な1列・BOM・引用符・改行を受け入れる: %s", async (csv) => {
    const rows = await parse(new File([csv], "test.csv", { type: "text/csv" }));
    expect(rows.length).toBeGreaterThan(0);
    expect(rows[0]["comment-body"]).toBeTruthy();
  });
});

it("Shift_JISの日本語を変換して読み込む", async () => {
  const bytes = Uint8Array.from(
    iconv.encode("comment-body,age\n公園を増やしてほしい,20\n交通を改善してほしい,30", "shift_jis"),
  );
  const rows = await parse(new File([bytes], "shift-jis.csv", { type: "text/csv" }));
  expect(rows[0]["comment-body"]).toBe("公園を増やしてほしい");
});
