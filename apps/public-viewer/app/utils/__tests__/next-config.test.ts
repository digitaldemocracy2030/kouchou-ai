/**
 * @jest-environment node
 */
import type { NextConfig } from "next";

const ORIGINAL_ENV = process.env;

function loadConfig(env: Record<string, string | undefined>): NextConfig {
  process.env = { ...ORIGINAL_ENV, ...env };
  let config: NextConfig | undefined;
  jest.isolateModules(() => {
    config = require("../../../next.config").default;
  });
  if (!config) throw new Error("next.config not loaded");
  return config;
}

afterEach(() => {
  process.env = ORIGINAL_ENV;
});

describe("next.config rewrites", () => {
  it("サーバーモードでは /meta/* を API に転送する（public/meta をコピーしないため）", async () => {
    const config = loadConfig({
      NEXT_PUBLIC_OUTPUT_MODE: undefined,
      API_BASEPATH: "http://api:8000/",
      NEXT_PUBLIC_API_BASEPATH: "http://localhost:8000",
    });
    expect(config.rewrites).toBeDefined();
    const rewrites = await config.rewrites?.();
    expect(rewrites).toEqual([{ source: "/meta/:path*", destination: "http://api:8000/meta/:path*" }]);
  });

  it("静的書き出しでは copy-image が public/meta に置くので転送しない", async () => {
    const config = loadConfig({ NEXT_PUBLIC_OUTPUT_MODE: "export", API_BASEPATH: "http://api:8000" });
    const rewrites = config.rewrites ? await config.rewrites() : [];
    expect(rewrites).toEqual([]);
  });
});
