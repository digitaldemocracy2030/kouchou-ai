import { type CostEstimateInput, JPY_PER_USD, estimateCost, estimateTokens, formatUsdRange } from "./costEstimate";

const prompt = {
  extraction: "p".repeat(639),
  initialLabelling: "p".repeat(463),
  mergeLabelling: "p".repeat(816),
  overview: "p".repeat(214),
};
const gpt4oMini = { input: 0.15, output: 0.6 };
const embeddingSmall = { input: 0.02, output: 0 };
function input(overrides: Partial<CostEstimateInput> = {}, count = 300, chars = 60): CostEstimateInput {
  return {
    comments: Array.from({ length: count }, () => ({ comment: "あ".repeat(chars) })),
    cluster: [5, 50],
    prompt,
    analysisMode: "hierarchical",
    chat: { model: "gpt-4o-mini", price: gpt4oMini, billed: true },
    embedding: { model: "text-embedding-3-small", price: embeddingSmall, billed: true },
    ...overrides,
  };
}

describe("estimateTokens", () => {
  test("空・空白のみのコメントは数えず、件数 0 ならトークンも 0", () => {
    const tokens = estimateTokens({ ...input(), comments: [{ comment: " " }, { comment: "" }, {}] });
    expect(tokens.commentCount).toBe(0);
    expect(tokens.chatInput).toEqual({ low: 0, high: 0 });
    expect(tokens.chatOutput).toEqual({ low: 0, high: 0 });
    expect(tokens.embedding).toEqual({ low: 0, high: 0 });
  });

  test("コメントが増えればチャット・埋め込みともに増え、low < high の幅になる", () => {
    const small = estimateTokens(input({}, 100));
    const large = estimateTokens(input({}, 1000));
    expect(small.commentCount).toBe(100);
    expect(large.chatInput.low).toBeGreaterThan(small.chatInput.low);
    expect(large.embedding.low).toBeGreaterThan(small.embedding.low);
    expect(small.chatInput.low).toBeLessThan(small.chatInput.high);
  });

  test("aipubcom 相当（2,916 件・平均 546 文字・gpt-4o-mini）の幅に実測 $0.87 が入る", () => {
    const estimate = estimateCost(input({ cluster: [10, 100] }, 2916, 546));
    expect(estimate.chat.kind).toBe("usd");
    expect(estimate.knownUsd.low).toBeLessThan(0.87);
    expect(estimate.knownUsd.high).toBeGreaterThan(0.87);
    expect(estimate.knownUsd.high).toBeLessThan(0.87 * 3);
  });

  test("LLM 直接グルーピングでも桁は変わらない", () => {
    const hierarchical = estimateTokens(input());
    const grouping = estimateTokens(input({ analysisMode: "llm_grouping" }));
    expect(grouping.chatInput.high).toBeGreaterThan(hierarchical.chatInput.high / 3);
    expect(grouping.chatInput.high).toBeLessThan(hierarchical.chatInput.high * 3);
  });
});

describe("estimateCost", () => {
  test("チャット単価が不明なら 0 円にせず unknown にし、既知の埋め込み分だけを分けて返す", () => {
    const estimate = estimateCost(input({ chat: { model: "my-local-model", price: null, billed: true } }));
    expect(estimate.chat).toEqual({ kind: "unknown", model: "my-local-model" });
    expect(estimate.band).toBe("unknown");
    expect(estimate.hasUnknown).toBe(true);
    expect(estimate.embedding.kind).toBe("usd");
    if (estimate.embedding.kind === "usd") expect(estimate.knownUsd).toEqual(estimate.embedding.usd);
  });

  test("埋め込み単価が不明なら帯はチャット分で決め、不明があることを示す", () => {
    const estimate = estimateCost(
      input({ embedding: { model: "gemini-embedding-001", price: undefined, billed: true } }),
    );
    expect(estimate.embedding).toEqual({ kind: "unknown", model: "gemini-embedding-001" });
    expect(estimate.hasUnknown).toBe(true);
    expect(estimate.band).toBe("under_100_yen");
    if (estimate.chat.kind === "usd") expect(estimate.knownUsd).toEqual(estimate.chat.usd);
  });

  test("サーバ内埋め込みは課金なしとして扱い、合計に含めない", () => {
    const billed = estimateCost(input());
    const local = estimateCost(
      input({ embedding: { model: "text-embedding-3-small", price: embeddingSmall, billed: false } }),
    );
    expect(local.embedding).toEqual({ kind: "not_billed", model: "text-embedding-3-small" });
    expect(local.hasUnknown).toBe(false);
    expect(local.knownUsd.high).toBeLessThan(billed.knownUsd.high);
  });

  test("ローカル LLM とサーバ内埋め込みの組み合わせは API 利用料なし", () => {
    const estimate = estimateCost(
      input({
        chat: { model: "llama3", price: null, billed: false },
        embedding: { model: "", price: null, billed: false },
      }),
    );
    expect(estimate.band).toBe("none");
    expect(estimate.knownUsd).toEqual({ low: 0, high: 0 });
    expect(estimate.hasUnknown).toBe(false);
  });

  test("件数 0 なら費用も 0", () => {
    const estimate = estimateCost(input({ comments: [] }));
    expect(estimate.commentCount).toBe(0);
    expect(estimate.knownUsd).toEqual({ low: 0, high: 0 });
    expect(estimate.band).toBe("under_100_yen");
  });

  test("帯は高めの見積もりを円に換算して決める（100 円・1,000 円が境界）", () => {
    const bandOf = (count: number) => {
      const estimate = estimateCost(input({}, count, 300));
      return { band: estimate.band, yen: estimate.knownUsd.high * JPY_PER_USD };
    };
    const small = bandOf(50);
    expect(small.yen).toBeLessThan(100);
    expect(small.band).toBe("under_100_yen");
    const middle = bandOf(2000);
    expect(middle.yen).toBeGreaterThanOrEqual(100);
    expect(middle.yen).toBeLessThan(1000);
    expect(middle.band).toBe("100_to_1000_yen");
    const large = bandOf(30000);
    expect(large.yen).toBeGreaterThanOrEqual(1000);
    expect(large.band).toBe("over_1000_yen");
  });

  test("単価が高いモデルほど高い", () => {
    const cheap = estimateCost(input());
    const expensive = estimateCost(
      input({ chat: { model: "gpt-4o", price: { input: 2.5, output: 10 }, billed: true } }),
    );
    expect(expensive.knownUsd.low).toBeGreaterThan(cheap.knownUsd.low);
  });
});

describe("formatUsdRange", () => {
  test("1 セント未満と、丸めて同じになる幅をまとめる", () => {
    expect(formatUsdRange({ low: 0.001, high: 0.004 })).toBe("$0.01未満");
    expect(formatUsdRange({ low: 0.004, high: 0.02 })).toBe("$0.01未満〜$0.02");
    expect(formatUsdRange({ low: 0.123, high: 0.456 })).toBe("$0.12〜$0.46");
    expect(formatUsdRange({ low: 1.001, high: 1.004 })).toBe("$1.00");
  });
});
