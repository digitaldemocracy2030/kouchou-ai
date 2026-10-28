// レポート作成前に表示する API 利用料の目安（#79）。
//
// 目的は精密な請求額の予測ではなく、実行前に「高額だったら怖い」を桁の見積もりで下げること。
// トークンは数えず（tiktoken 等の依存は入れない）、入力コメントの文字数 × 係数で幅を持たせる。
// 係数は analysis-core の各ステップが LLM に送る内容（2026-10 時点の main）から読み取り、
// aipubcom（2,916 件・コメント本文 4,775,111 bytes・実測 $0.87、gpt-4o-mini、2025-03）で桁を確かめた。
// 単価が分からない部分は 0 円にせず「単価不明」として分けて返す。

/** 日本語 1 文字あたりのトークン数の幅。o200k 系（GPT-4o 以降）で 0.7〜1.0、cl100k や Gemini 系で 1 前後〜1.5。 */
export const TOKENS_PER_CHAR = { low: 0.7, high: 1.5 } as const;
/** 1 回の呼び出しで本文の他に入力側へ乗るトークン（メッセージの枠、構造化出力の JSON スキーマ）。 */
export const CALL_INPUT_OVERHEAD_TOKENS = 50;
/** 1 回の呼び出しで本文の他に出力側へ乗るトークン（JSON のキー・括弧）。 */
export const CALL_OUTPUT_OVERHEAD_TOKENS = 20;
/**
 * コメント 1 件（c 文字）から抽出される意見の合計文字数。
 * aipubcom では平均 546 文字のコメントから平均 160 文字（3.4 件 × 47 文字）の意見が出た（係数 0.3）。
 * 短いコメントは 1 件がほぼそのまま 1 意見になるので定数項を足す。
 */
export const extractedCharsOf = (commentChars: number): number => 0.3 * commentChars + 40;
/** 抽出された意見 1 件の平均文字数（aipubcom の平均 47 文字）。意見件数と、ラベル生成に送る意見の量に使う。 */
export const AVERAGE_ARGUMENT_CHARS = 50;
/** ラベル生成 1 回の出力文字数（label 約 20 文字 + description 約 150 文字 + JSON）。 */
export const LABEL_OUTPUT_CHARS = 200;
/** 全体概要（overview）の出力文字数。 */
export const OVERVIEW_OUTPUT_CHARS = 400;
/** 初期・統合ラベル生成で 1 クラスタから送る意見の件数。apps/api の report_launcher が渡す sampling_num。 */
export const LABELLING_SAMPLING_NUM = 30;
/** LLM 直接グルーピング（analysis-core の llm_grouping_specs.json の既定値。管理画面からは変更できない）。 */
export const LLM_GROUPING = {
  discoverySampleSize: 80,
  assignmentBatchSize: 25,
  /** analysis-core 既定の discovery / assignment プロンプト（prompts/__init__.py）の文字数と、user メッセージの枠。 */
  discoveryPromptChars: 249,
  assignmentPromptChars: 181,
  assignmentFramingChars: 150,
  /** 割当応答の 1 意見あたりのトークン（{"arg_id": "A123_0", "group_id": "g1"}）。 */
  assignmentOutputTokensPerArgument: 20,
} as const;
/** 円の帯を決めるためだけの粗い換算値。表示にも明記する。 */
export const JPY_PER_USD = 150;

/** 100 万トークンあたりの USD 単価。null / undefined は単価不明。埋め込みは input だけを使う。 */
export type UnitPrice = { input: number; output: number } | null | undefined;

export type Range = { low: number; high: number };

export type CostEstimateInput = {
  /** 取り込み後のコメント配列。空・空白のみの行は analysis-core と同様に数えない。 */
  comments: ReadonlyArray<{ comment?: unknown }>;
  /** [第 1 階層, 第 2 階層] の意見グループ数。 */
  cluster: readonly [number, number];
  /** 実際に送るプロンプト（文字数だけを使う）。 */
  prompt: { extraction: string; initialLabelling: string; mergeLabelling: string; overview: string };
  /** "hierarchical"（既定）か "llm_grouping"。 */
  analysisMode: string;
  /** billed=false はローカル LLM など API 利用料がかからない構成。 */
  chat: { model: string; price: UnitPrice; billed: boolean };
  /** billed=false はサーバ内埋め込み（ローカルモデル）。 */
  embedding: { model: string; price: UnitPrice; billed: boolean };
};

export type SlotEstimate =
  | { kind: "not_billed"; model: string }
  | { kind: "unknown"; model: string }
  | { kind: "usd"; model: string; usd: Range };

/**
 * 円の帯。既知部分の高めの見積もりで決める（安く見せないため）。
 * - unknown: チャット単価が不明で、費用の大半を占める部分が見積もれない
 * - none: チャットも埋め込みも課金されない構成
 */
export type CostBand = "unknown" | "none" | "under_100_yen" | "100_to_1000_yen" | "over_1000_yen";

export type CostEstimate = {
  commentCount: number;
  commentChars: number;
  tokens: { chatInput: Range; chatOutput: Range; embedding: Range };
  chat: SlotEstimate;
  embedding: SlotEstimate;
  /** 単価が分かっている部分だけの合計（USD）。単価不明の部分は含まない。 */
  knownUsd: Range;
  /** 単価不明の部分があるか（0 円扱いにしていないことを表示側で明示する）。 */
  hasUnknown: boolean;
  band: CostBand;
};

const zero: Range = { low: 0, high: 0 };
const add = (a: Range, b: Range): Range => ({ low: a.low + b.low, high: a.high + b.high });
/** 文字数をトークン数の幅にする。fixedTokens は本文に依存しない分で、幅を付けない。 */
const tokensOf = (chars: number, fixedTokens = 0): Range => ({
  low: chars * TOKENS_PER_CHAR.low + fixedTokens,
  high: chars * TOKENS_PER_CHAR.high + fixedTokens,
});

/** 各ステップのトークン量（文字数ベース）。チャットの input / output と埋め込みを分けて返す。 */
export function estimateTokens(input: Omit<CostEstimateInput, "chat" | "embedding">): CostEstimate["tokens"] & {
  commentCount: number;
  commentChars: number;
} {
  const bodies = input.comments
    .map((row) => (typeof row.comment === "string" ? row.comment : ""))
    .filter((body) => body.trim());
  const n = bodies.length;
  const commentChars = bodies.reduce((sum, body) => sum + body.length, 0);
  if (n === 0) {
    return { commentCount: 0, commentChars: 0, chatInput: zero, chatOutput: zero, embedding: zero };
  }

  // 抽出: コメント 1 件 = 1 呼び出し（system = 抽出プロンプト、user = コメント本文）。
  const extractedChars = extractedCharsOf(commentChars / n) * n;
  const argumentCount = Math.max(1, Math.round(extractedChars / AVERAGE_ARGUMENT_CHARS));
  const argumentChars = extractedChars / argumentCount;
  let chatInput = tokensOf(n * input.prompt.extraction.length + commentChars, n * CALL_INPUT_OVERHEAD_TOKENS);
  let chatOutput = tokensOf(extractedChars, n * CALL_OUTPUT_OVERHEAD_TOKENS);

  // 埋め込み: 抽出された意見の本文を全件送る（is_embedded_at_local なら課金側で除く）。
  const embedding = tokensOf(extractedChars);

  const [lv1, lv2] = input.cluster;
  let topLevelCount: number;
  if (input.analysisMode === "llm_grouping") {
    // グループ数は管理画面の値ではなく、analysis-core が意見件数から決める（calculate_recommended_cluster_nums の第 1 階層）。
    topLevelCount = Math.max(2, Math.min(10, Math.round(Math.cbrt(argumentCount))));
    const groupChars = topLevelCount * LABEL_OUTPUT_CHARS;
    // 発見: 1 呼び出し（意見を 80 件サンプル）。
    const discoverySample = Math.min(LLM_GROUPING.discoverySampleSize, argumentCount);
    chatInput = add(
      chatInput,
      tokensOf(LLM_GROUPING.discoveryPromptChars + discoverySample * argumentChars, CALL_INPUT_OVERHEAD_TOKENS),
    );
    chatOutput = add(chatOutput, tokensOf(groupChars, CALL_OUTPUT_OVERHEAD_TOKENS));
    // 割当: 25 件ずつのバッチごとに 1 呼び出し（グループ定義 + 意見一覧）。出力は id の対応だけ。
    const batches = Math.ceil(argumentCount / LLM_GROUPING.assignmentBatchSize);
    chatInput = add(
      chatInput,
      tokensOf(
        batches * (LLM_GROUPING.assignmentPromptChars + LLM_GROUPING.assignmentFramingChars + groupChars) +
          argumentCount * (argumentChars + 12),
        batches * CALL_INPUT_OVERHEAD_TOKENS,
      ),
    );
    chatOutput = add(chatOutput, {
      low: argumentCount * LLM_GROUPING.assignmentOutputTokensPerArgument + batches * CALL_OUTPUT_OVERHEAD_TOKENS,
      high: argumentCount * LLM_GROUPING.assignmentOutputTokensPerArgument + batches * CALL_OUTPUT_OVERHEAD_TOKENS,
    });
  } else {
    topLevelCount = lv1;
    const bottomCount = Math.max(1, Math.min(lv2, argumentCount));
    // 初期ラベル: 第 2 階層のクラスタごとに 1 呼び出し（プロンプト + 意見を最大 30 件）。
    const initialSample = Math.min(LABELLING_SAMPLING_NUM, Math.ceil(argumentCount / bottomCount));
    chatInput = add(
      chatInput,
      tokensOf(
        bottomCount * (input.prompt.initialLabelling.length + initialSample * argumentChars),
        bottomCount * CALL_INPUT_OVERHEAD_TOKENS,
      ),
    );
    chatOutput = add(chatOutput, tokensOf(bottomCount * LABEL_OUTPUT_CHARS, bottomCount * CALL_OUTPUT_OVERHEAD_TOKENS));
    // 統合ラベル: 第 1 階層のクラスタごとに 1 呼び出し（プロンプト + 子クラスタのラベル・説明 + 意見を最大 30 件）。
    const upperCount = Math.max(1, Math.min(lv1, bottomCount));
    const mergeSample = Math.min(LABELLING_SAMPLING_NUM, Math.ceil(argumentCount / upperCount));
    chatInput = add(
      chatInput,
      tokensOf(
        upperCount *
          (input.prompt.mergeLabelling.length +
            (bottomCount / upperCount) * LABEL_OUTPUT_CHARS +
            mergeSample * argumentChars),
        upperCount * CALL_INPUT_OVERHEAD_TOKENS,
      ),
    );
    chatOutput = add(chatOutput, tokensOf(upperCount * LABEL_OUTPUT_CHARS, upperCount * CALL_OUTPUT_OVERHEAD_TOKENS));
  }

  // 全体概要: 1 呼び出し（プロンプト + 第 1 階層のラベル・説明）。
  chatInput = add(
    chatInput,
    tokensOf(input.prompt.overview.length + topLevelCount * LABEL_OUTPUT_CHARS, CALL_INPUT_OVERHEAD_TOKENS),
  );
  chatOutput = add(chatOutput, tokensOf(OVERVIEW_OUTPUT_CHARS, CALL_OUTPUT_OVERHEAD_TOKENS));

  return { commentCount: n, commentChars, chatInput, chatOutput, embedding };
}

const isKnownPrice = (price: UnitPrice): price is { input: number; output: number } =>
  !!price && Number.isFinite(price.input) && Number.isFinite(price.output);

export function estimateCost(input: CostEstimateInput): CostEstimate {
  const tokens = estimateTokens(input);
  const { commentCount, commentChars, ...tokenRanges } = tokens;

  const chat: SlotEstimate = !input.chat.billed
    ? { kind: "not_billed", model: input.chat.model }
    : !isKnownPrice(input.chat.price)
      ? { kind: "unknown", model: input.chat.model }
      : {
          kind: "usd",
          model: input.chat.model,
          usd: {
            low:
              (tokens.chatInput.low * input.chat.price.input + tokens.chatOutput.low * input.chat.price.output) / 1e6,
            high:
              (tokens.chatInput.high * input.chat.price.input + tokens.chatOutput.high * input.chat.price.output) / 1e6,
          },
        };
  const embedding: SlotEstimate = !input.embedding.billed
    ? { kind: "not_billed", model: input.embedding.model }
    : !isKnownPrice(input.embedding.price)
      ? { kind: "unknown", model: input.embedding.model }
      : {
          kind: "usd",
          model: input.embedding.model,
          usd: {
            low: (tokens.embedding.low * input.embedding.price.input) / 1e6,
            high: (tokens.embedding.high * input.embedding.price.input) / 1e6,
          },
        };

  const knownUsd = [chat, embedding].reduce((sum, slot) => (slot.kind === "usd" ? add(sum, slot.usd) : sum), zero);
  const hasUnknown = chat.kind === "unknown" || embedding.kind === "unknown";

  let band: CostBand;
  if (chat.kind === "unknown") {
    band = "unknown";
  } else if (chat.kind === "not_billed" && embedding.kind !== "usd") {
    band = embedding.kind === "unknown" ? "unknown" : "none";
  } else {
    const yen = knownUsd.high * JPY_PER_USD;
    band = yen < 100 ? "under_100_yen" : yen < 1000 ? "100_to_1000_yen" : "over_1000_yen";
  }

  return { commentCount, commentChars, tokens: tokenRanges, chat, embedding, knownUsd, hasUnknown, band };
}

/** USD の幅を表示用にする。1 セント未満は「$0.01未満」、丸めて同じ値になる幅は 1 つの値で出す。 */
export function formatUsdRange(range: Range): string {
  const format = (usd: number) => (usd < 0.01 ? "$0.01未満" : `$${usd.toFixed(2)}`);
  const low = format(range.low);
  const high = format(range.high);
  return low === high ? low : `${low}〜${high}`;
}
