/**
 * @jest-environment node
 */
import { resolveUrl } from "next/dist/lib/metadata/resolvers/resolve-url";

jest.mock("@/components/ApiConnectionError", () => ({ ApiConnectionError: () => null }));
jest.mock("@/components/report/ReportShell", () => ({ ReportShell: () => null }));
jest.mock("@/components/report/ReportView", () => ({ ReportView: () => null }));
jest.mock("@/components/reporter/Reporter", () => ({ Reporter: () => null }));

const ORIGINAL_ENV = process.env;

async function generateMetadataWith(env: Record<string, string | undefined>) {
  process.env = { ...ORIGINAL_ENV, ...env };
  let mod: typeof import("../page") | undefined;
  jest.isolateModules(() => {
    mod = require("../page");
  });
  if (!mod) throw new Error("page not loaded");
  return mod.generateMetadata({ params: Promise.resolve({ slug: "my-report" }) });
}

beforeEach(() => {
  global.fetch = jest.fn(async (url: string | URL | Request) =>
    String(url).endsWith("/meta/metadata.json")
      ? new Response(JSON.stringify({ reporter: "テスト" }))
      : new Response(JSON.stringify({ config: { question: "問い" }, overview: "概要", visibility: "public" })),
  ) as unknown as typeof fetch;
  jest.spyOn(console, "warn").mockImplementation(() => {});
});

afterEach(() => {
  process.env = ORIGINAL_ENV;
  jest.restoreAllMocks();
});

describe("[slug] generateMetadata（静的書き出し）", () => {
  it("og:image を NEXT_PUBLIC_SITE_URL とベースパス付きの絶対 URL に解決させる", async () => {
    const metadata = await generateMetadataWith({
      NEXT_PUBLIC_OUTPUT_MODE: "export",
      NEXT_PUBLIC_STATIC_SHELL: undefined,
      NEXT_PUBLIC_SITE_URL: "https://example.org/",
      NEXT_PUBLIC_STATIC_EXPORT_BASE_PATH: "/kouchou",
      API_BASEPATH: "http://api:8000",
    });

    expect(metadata.metadataBase).toBeInstanceOf(URL);
    const images = metadata.openGraph?.images as string[];
    // Next はこの組み合わせで og:image の絶対 URL を作る
    expect(resolveUrl(images[0], metadata.metadataBase as URL)?.href).toBe(
      "https://example.org/kouchou/my-report/opengraph-image.png",
    );
  });

  it("NEXT_PUBLIC_SITE_URL が未設定なら警告する", async () => {
    await generateMetadataWith({
      NEXT_PUBLIC_OUTPUT_MODE: "export",
      NEXT_PUBLIC_STATIC_SHELL: undefined,
      NEXT_PUBLIC_SITE_URL: undefined,
      API_BASEPATH: "http://api:8000",
    });
    expect(console.warn).toHaveBeenCalledWith(expect.stringContaining("NEXT_PUBLIC_SITE_URL"));
  });
});
