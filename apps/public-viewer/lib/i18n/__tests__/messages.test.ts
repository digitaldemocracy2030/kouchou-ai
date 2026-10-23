import { SUPPORTED_LANGUAGES } from "../languages";
import { getMessages, messages } from "../messages";

describe("messages", () => {
  it("全言語で同じキーを持つ", () => {
    const jaKeys = Object.keys(messages.ja).sort();
    for (const lang of SUPPORTED_LANGUAGES) {
      expect(Object.keys(messages[lang]).sort()).toEqual(jaKeys);
      expect(Object.keys(messages[lang].chartModes).sort()).toEqual(Object.keys(messages.ja.chartModes).sort());
      expect(Object.keys(messages[lang].steps).sort()).toEqual(Object.keys(messages.ja.steps).sort());
      expect(messages[lang].readingGuideItems).toHaveLength(messages.ja.readingGuideItems.length);
    }
  });

  it("件数の表記は言語ごとに変わる", () => {
    expect(getMessages("ja").opinionCount(1234)).toBe("1,234件");
    expect(getMessages("en").opinionCount(1234)).toBe("1,234 opinions");
    expect(getMessages("ko").opinionCount(1234)).toBe("1,234건");
  });

  it("読み方の日本語文言は serverless と揃えた原文のまま (#696)", () => {
    expect(messages.ja.readingGuideLead).toBe(
      "このレポートは、集めた意見から論点や課題を見つけるためのものです。表示される件数は、社会全体の支持率を示すものではありません。",
    );
  });
});
