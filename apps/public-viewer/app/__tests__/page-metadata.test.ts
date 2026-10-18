/**
 * @jest-environment node
 */
import { resolveUrl } from "next/dist/lib/metadata/resolvers/resolve-url";

jest.mock("@/components/ApiConnectionError", () => ({ ApiConnectionError: () => null }));
jest.mock("@/components/report/ReportListShell", () => ({ ReportListShell: () => null }));
jest.mock("@/components/report/ReportListView", () => ({ ReportListView: () => null }));
jest.mock("@/components/reporter/Reporter", () => ({ Reporter: () => null }));

const ORIGINAL_ENV = process.env;

afterEach(() => {
  process.env = ORIGINAL_ENV;
});

describe("トップページの generateMetadata（静的書き出し）", () => {
  it("og:image を NEXT_PUBLIC_SITE_URL とベースパス付きの絶対 URL に解決させる", async () => {
    process.env = {
      ...ORIGINAL_ENV,
      NEXT_PUBLIC_OUTPUT_MODE: "export",
      NEXT_PUBLIC_STATIC_SHELL: undefined,
      NEXT_PUBLIC_SITE_URL: "https://example.org",
      NEXT_PUBLIC_STATIC_EXPORT_BASE_PATH: "/kouchou",
      API_BASEPATH: "http://api:8000",
    };
    global.fetch = jest.fn(async () => new Response(JSON.stringify({ reporter: "テスト" }))) as unknown as typeof fetch;
    let mod: typeof import("../page") | undefined;
    jest.isolateModules(() => {
      mod = require("../page");
    });
    if (!mod) throw new Error("page not loaded");

    const metadata = await mod.generateMetadata();
    const images = metadata.openGraph?.images as string[];
    expect(resolveUrl(images[0], metadata.metadataBase as URL)?.href).toBe("https://example.org/kouchou/meta/ogp.png");
  });
});
