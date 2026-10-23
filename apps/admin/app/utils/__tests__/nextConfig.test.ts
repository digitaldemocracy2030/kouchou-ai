import nextConfig from "../../../next.config";

// bytes パッケージ（Next が設定値の解釈に使う）と同じく 1kb = 1024 として数える
function parseSize(value: unknown): number {
  if (typeof value === "number") return value;
  const match = /^(\d+(?:\.\d+)?)\s*(b|kb|mb|gb)$/i.exec(String(value));
  if (!match) throw new Error(`unexpected size: ${String(value)}`);
  const unit = { b: 1, kb: 1024, mb: 1024 ** 2, gb: 1024 ** 3 }[match[2].toLowerCase() as "b" | "kb" | "mb" | "gb"];
  return Number(match[1]) * unit;
}

describe("next.config の本文サイズ上限", () => {
  const experimental = nextConfig.experimental ?? {};

  it("middleware が本文を複製するときの上限を、Server Action の上限より大きくする", () => {
    // middleware.ts（Basic 認証）は全パスで走り、Next はそのために本文を複製する。複製の上限
    // （proxyClientMaxBodySize、既定 10MB）が小さいと、bodySizeLimit を 100mb にしても本文が
    // 10MB で切れ、createReport の JSON の解析に失敗して 500 になる（s002）。
    const serverActionLimit = parseSize(experimental.serverActions?.bodySizeLimit);
    expect(serverActionLimit).toBeGreaterThan(10 * 1024 * 1024);
    expect(experimental.proxyClientMaxBodySize).toBeDefined();
    // 同じ値だと、上限を超えた本文が上限の長さに切り詰められて Server Action の検査を通り、
    // 「Body exceeded 100mb limit」ではなく、原因の分からない JSON の解析エラーになる
    expect(parseSize(experimental.proxyClientMaxBodySize)).toBeGreaterThan(serverActionLimit);
  });

  it("旧名の middlewareClientMaxBodySize とは同時に指定しない（Next が設定読み込みで例外を投げる）", () => {
    expect(experimental).not.toHaveProperty("middlewareClientMaxBodySize");
  });
});
