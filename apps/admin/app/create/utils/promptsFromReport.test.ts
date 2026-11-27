import {
  DEFAULT_PROMPTS,
  type PromptValues,
  editedSinceLoad,
  formatPromptKeys,
  planPromptLoad,
  promptSourceLabel,
  promptsFromReportConfig,
  sortPromptSourceReports,
} from "./promptsFromReport";

const hierarchicalConfig = {
  analysis_mode: "hierarchical",
  extraction: { prompt: "抽出（調整済み）", workers: 30 },
  hierarchical_initial_labelling: { prompt: "初期ラベリング（調整済み）" },
  hierarchical_merge_labelling: { prompt: "統合ラベリング（調整済み）" },
  hierarchical_overview: { prompt: "要約（調整済み）" },
};

describe("promptsFromReportConfig", () => {
  it("各工程のプロンプトをフォームの値に写す", () => {
    expect(promptsFromReportConfig(hierarchicalConfig)).toEqual({
      extraction: "抽出（調整済み）",
      initialLabelling: "初期ラベリング（調整済み）",
      mergeLabelling: "統合ラベリング（調整済み）",
      overview: "要約（調整済み）",
    });
  });

  it("LLM 直接グルーピングのレポートには初期・統合ラベリングが無いので含めない", () => {
    expect(
      promptsFromReportConfig({
        analysis_mode: "llm_grouping",
        extraction: { prompt: "抽出" },
        hierarchical_overview: { prompt: "要約" },
      }),
    ).toEqual({ extraction: "抽出", overview: "要約" });
  });

  it("空や null のプロンプト、config が無い場合は何も返さない", () => {
    expect(
      promptsFromReportConfig({
        extraction: { prompt: "  " },
        hierarchical_initial_labelling: null,
        hierarchical_overview: { prompt: null },
      }),
    ).toEqual({});
    expect(promptsFromReportConfig(null)).toEqual({});
    expect(promptsFromReportConfig(undefined)).toEqual({});
  });
});

describe("planPromptLoad", () => {
  it("既定のままなら確認なしで全工程を読み込む", () => {
    const plan = planPromptLoad(DEFAULT_PROMPTS, hierarchicalConfig);
    expect(plan.loaded).toEqual(["extraction", "initialLabelling", "mergeLabelling", "overview"]);
    expect(plan.missing).toEqual([]);
    expect(plan.overwritten).toEqual([]);
    expect(plan.next.extraction).toBe("抽出（調整済み）");
    expect(plan.next.overview).toBe("要約（調整済み）");
  });

  it("利用者が書き換えた工程は上書きとして数える", () => {
    const current: PromptValues = { ...DEFAULT_PROMPTS, extraction: "自分で書いた抽出", overview: "自分で書いた要約" };
    const plan = planPromptLoad(current, hierarchicalConfig);
    expect(plan.overwritten).toEqual(["extraction", "overview"]);
  });

  it("書き換えた内容が読み込む内容と同じなら上書きに数えない", () => {
    const current: PromptValues = { ...DEFAULT_PROMPTS, extraction: "抽出（調整済み）" };
    expect(planPromptLoad(current, hierarchicalConfig).overwritten).toEqual([]);
  });

  it("手本に無い工程は今の内容を残し、上書きにも数えない", () => {
    const current: PromptValues = { ...DEFAULT_PROMPTS, initialLabelling: "自分で書いた初期ラベリング" };
    const plan = planPromptLoad(current, {
      analysis_mode: "llm_grouping",
      extraction: { prompt: "抽出（調整済み）" },
      hierarchical_overview: { prompt: "要約（調整済み）" },
    });
    expect(plan.loaded).toEqual(["extraction", "overview"]);
    expect(plan.missing).toEqual(["initialLabelling", "mergeLabelling"]);
    expect(plan.overwritten).toEqual([]);
    expect(plan.next.initialLabelling).toBe("自分で書いた初期ラベリング");
    expect(plan.next.mergeLabelling).toBe(DEFAULT_PROMPTS.mergeLabelling);
  });

  it("元の値を書き換えない", () => {
    const current: PromptValues = { ...DEFAULT_PROMPTS };
    planPromptLoad(current, hierarchicalConfig);
    expect(current).toEqual(DEFAULT_PROMPTS);
  });
});

describe("editedSinceLoad", () => {
  it("読み込んだ後に変えた工程だけを返す", () => {
    const { next, loaded } = planPromptLoad(DEFAULT_PROMPTS, hierarchicalConfig);
    expect(editedSinceLoad(next, next, loaded)).toEqual([]);
    expect(editedSinceLoad({ ...next, overview: "編集した要約" }, next, loaded)).toEqual(["overview"]);
  });
});

describe("表示用の補助", () => {
  it("工程名を・でつなぐ", () => {
    expect(formatPromptKeys(["extraction", "overview"])).toBe("抽出・要約");
  });

  it("タイトルと ID を並べ、タイトルが無ければ ID だけにする", () => {
    expect(promptSourceLabel({ slug: "group-a", title: "グループA" })).toBe("グループA（group-a）");
    expect(promptSourceLabel({ slug: "group-b", title: "" })).toBe("group-b");
  });

  it("新しいレポートを先に並べ、作成日時が無いものは最後にする", () => {
    const sorted = sortPromptSourceReports([
      { slug: "old", title: "", createdAt: "2026-01-01T00:00:00Z" },
      { slug: "unknown", title: "" },
      { slug: "new", title: "", createdAt: "2026-11-01T00:00:00Z" },
    ]);
    expect(sorted.map((report) => report.slug)).toEqual(["new", "old", "unknown"]);
  });
});
