import type { Result } from "@/type";
import { getReportTranslation, hasReportTranslation, localizeResult } from "../translateResult";

function makeResult(translations?: Result["translations"]): Result {
  return {
    arguments: [
      { arg_id: "A1", argument: "バスを増やしてほしい", comment_id: 1, x: 0, y: 0, p: 0, cluster_ids: ["0", "1"] },
      { arg_id: "A2", argument: "駅前に駐輪場が欲しい", comment_id: 2, x: 1, y: 1, p: 0, cluster_ids: ["0", "2"] },
    ],
    clusters: [
      { level: 0, id: "0", label: "全体", takeaway: "", value: 2, parent: "", density_rank_percentile: 0 },
      { level: 1, id: "1", label: "交通", takeaway: "交通の説明", value: 1, parent: "0", density_rank_percentile: 0 },
      {
        level: 1,
        id: "2",
        label: "自転車",
        takeaway: "自転車の説明",
        value: 1,
        parent: "0",
        density_rank_percentile: 0,
      },
    ],
    comments: {},
    propertyMap: {},
    translations,
    overview: "全体の概要",
    config: { question: "まちの課題は？", intro: "イントロ" } as unknown as Result["config"],
    comment_num: 2,
  };
}

describe("getReportTranslation", () => {
  it("translations が無い・空・対象言語が無いときは undefined", () => {
    expect(getReportTranslation(undefined, "en")).toBeUndefined();
    expect(getReportTranslation({}, "en")).toBeUndefined();
    expect(getReportTranslation({ ko: { overview: "x" } }, "en")).toBeUndefined();
    expect(getReportTranslation({ en: {} }, "en")).toBeUndefined();
    expect(getReportTranslation({ en: "not an object" }, "en")).toBeUndefined();
  });

  it("構造化された翻訳を正規化し、型が合わない値は落とす", () => {
    const t = getReportTranslation(
      {
        en: {
          clusters: { "1": { label: "Transport", takeaway: 5 }, "2": { label: "" }, "3": "bad" },
          overview: "Overview",
          question: 1,
          arguments: { A1: "More buses", A2: 2 },
        },
      },
      "en",
    );
    expect(t).toEqual({
      clusters: { "1": { label: "Transport" } },
      overview: "Overview",
      arguments: { A1: "More buses" },
    });
  });

  it("言語コードの表記ゆれ（en-US / EN）を吸収する", () => {
    expect(getReportTranslation({ "en-US": { overview: "o" } }, "en")?.overview).toBe("o");
    expect(getReportTranslation({ en: { overview: "o" } }, "EN")?.overview).toBe("o");
  });

  it("旧形式（元の文字列 → 訳文）も読める", () => {
    expect(getReportTranslation({ en: { 交通: "Transport" } }, "en")).toEqual({ texts: { 交通: "Transport" } });
  });
});

describe("localizeResult", () => {
  it("翻訳が無いときは同じオブジェクトをそのまま返す", () => {
    const result = makeResult({});
    expect(localizeResult(result, "en")).toBe(result);
    const noTranslations = makeResult(undefined);
    expect(localizeResult(noTranslations, "ko")).toBe(noTranslations);
  });

  it("クラスタ・概要・問いを差し替え、無い文言は元のまま残す", () => {
    const result = makeResult({
      en: {
        clusters: { "0": { label: "All" }, "1": { label: "Transport", takeaway: "About transport" } },
        overview: "Overview in English",
        question: "What are the town's issues?",
      },
    });
    const localized = localizeResult(result, "en");
    expect(localized).not.toBe(result);
    expect(localized.clusters.map((c) => [c.label, c.takeaway])).toEqual([
      ["All", ""],
      ["Transport", "About transport"],
      ["自転車", "自転車の説明"],
    ]);
    expect(localized.overview).toBe("Overview in English");
    expect(localized.config.question).toBe("What are the town's issues?");
    expect(localized.config.intro).toBe("イントロ");
    // 意見の翻訳が無いので arguments は同じ参照（ClientContainer の memo を壊さない）
    expect(localized.arguments).toBe(result.arguments);
    // 翻訳されなかったクラスタも同じ参照
    expect(localized.clusters[2]).toBe(result.clusters[2]);
    // 元の Result は変更しない
    expect(result.clusters[1].label).toBe("交通");
  });

  it("意見の翻訳があれば arguments も差し替える", () => {
    const result = makeResult({ ko: { arguments: { A1: "버스를 늘려 주세요" } } });
    const localized = localizeResult(result, "ko");
    expect(localized.arguments[0].argument).toBe("버스를 늘려 주세요");
    expect(localized.arguments[1]).toBe(result.arguments[1]);
    expect(localized.clusters).toBe(result.clusters);
  });

  it("旧形式は元の文字列で引く", () => {
    const result = makeResult({ en: { 交通: "Transport", 全体の概要: "Overview" } });
    const localized = localizeResult(result, "en");
    expect(localized.clusters[1].label).toBe("Transport");
    expect(localized.overview).toBe("Overview");
  });

  it("hasReportTranslation は表示言語の翻訳の有無を返す", () => {
    const result = makeResult({ en: { overview: "o" } });
    expect(hasReportTranslation(result, "en")).toBe(true);
    expect(hasReportTranslation(result, "ko")).toBe(false);
    expect(hasReportTranslation(makeResult(undefined), "en")).toBe(false);
  });
});
