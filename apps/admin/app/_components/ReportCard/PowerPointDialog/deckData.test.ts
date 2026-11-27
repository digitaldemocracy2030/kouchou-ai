import { fitHeading, makeReportUrl } from "./createPowerPoint";
import { getDeckData } from "./deckData";

const result = {
  arguments: [
    { argument: "バスを増やす", cluster_ids: ["0", "1_0", "1_0"] },
    { argument: "バスを増やす", cluster_ids: ["0", "1_0"] },
    { argument: "図書館を建てる", cluster_ids: ["0", "1_1"] },
  ],
  clusters: [
    { level: 0, id: "0", label: "", takeaway: "" },
    { level: 1, id: "1_0", value: 100, label: "交通", takeaway: "移動手段" },
    { level: 1, id: "1_1", label: "公共施設", takeaway: "図書館" },
  ],
  config: { name: "town-survey", question: "まちに何が必要か" },
  overview: "概要",
  comment_num: 2,
  comments: { hide: { comment: "SLIDE_SECRET" } },
};

test("counts extracted opinions by membership and keeps input count separate", () => {
  const deck = getDeckData(result);
  expect(deck.inputCount).toBe(2);
  expect(deck.opinionCount).toBe(3);
  expect(deck.topics[0]).toEqual({
    id: "1_0",
    label: "交通",
    takeaway: "移動手段",
    count: 2,
    examples: ["バスを増やす"],
  });
  expect(JSON.stringify(deck)).not.toContain("SLIDE_SECRET");
  expect(getDeckData({ ...result, comment_num: undefined }).inputCount).toBeUndefined();
});

test("constructs a report link for a viewer hosted at a base path", () => {
  expect(makeReportUrl("/viewer/", "https://example.org", "report")?.href).toBe("https://example.org/viewer/report");
  expect(makeReportUrl("file:///report", "https://example.org", "report")).toBeUndefined();
});

test("uses the report title rather than the input identifier", () => {
  expect(getDeckData(result).title).toBe("まちに何が必要か");
  expect(getDeckData({ ...result, config: { name: "town-survey", question: "" } }).title).toBe("town-survey");
  expect(getDeckData({ ...result, config: undefined }).title).toBe("広聴AIレポート");
});

test("fits topic headings into the heading box", () => {
  expect(fitHeading("交通")).toEqual({ text: "交通", fontSize: 26 });
  expect(fitHeading("交通\n福祉\n教育\n環境")).toEqual({ text: "交通 福祉 教育 環境", fontSize: 26 });
  const long = fitHeading("あ".repeat(88));
  expect(long.text).toBe("あ".repeat(88));
  expect(long.fontSize).toBeLessThan(26);
  const tooLong = fitHeading("あ".repeat(300));
  expect(tooLong.fontSize).toBe(16);
  expect(tooLong.text.endsWith("…")).toBe(true);
  expect(Array.from(tooLong.text).length).toBeLessThan(300);
});
