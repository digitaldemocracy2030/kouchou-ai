import {
  SERVER_ACTION_BODY_SIZE_LIMIT_BYTES,
  estimateServerActionBodyBytes,
  utf8ByteLength,
} from "../requestBodyLimit";

describe("requestBodyLimit", () => {
  it("UTF-8 のバイト数を数える（ASCII・日本語・サロゲートペア）", () => {
    for (const text of ["", "abc", "意見", "é", "😀", "a意😀b", "\ud800"]) {
      expect(utf8ByteLength(text)).toBe(Buffer.byteLength(text, "utf8"));
    }
  });

  it("Server Action の本文は JSON.stringify([args]) のバイト数で見積もる", () => {
    const arg = { comments: [{ id: "1", comment: "意見" }] };
    expect(estimateServerActionBodyBytes(arg)).toBe(Buffer.byteLength(JSON.stringify([arg]), "utf8"));
  });

  it("上限は 100mb（1mb = 1024 * 1024 バイト）", () => {
    expect(SERVER_ACTION_BODY_SIZE_LIMIT_BYTES).toBe(100 * 1024 * 1024);
  });
});
