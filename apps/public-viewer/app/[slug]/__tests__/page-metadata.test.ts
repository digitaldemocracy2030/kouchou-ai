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
  // レポート別の OGP 画像（opengraph-image）は静的書き出しでは生成されないので、
  // copy-image が出力に置く共通画像 /meta/ogp.png を指す（トップページと同じ）
  it("og:image を、出力に存在する共通画像の NEXT_PUBLIC_SITE_URL とベースパス付きの絶対 URL に解決させる", async () => {
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
    expect(resolveUrl(images[0], metadata.metadataBase as URL)?.href).toBe("https://example.org/kouchou/meta/ogp.png");
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

describe("[slug] generateMetadata（metadata.json の項目欠け）", () => {
  it("reporter が null なら、タイトルは問いだけにして null を出さない", async () => {
    global.fetch = jest.fn(async (url: string | URL | Request) =>
      String(url).endsWith("/meta/metadata.json")
        ? new Response(JSON.stringify({ reporter: null, message: null, isDefault: false }))
        : new Response(JSON.stringify({ config: { question: "問い" }, overview: "概要", visibility: "public" })),
    ) as unknown as typeof fetch;
    const metadata = await generateMetadataWith({
      NEXT_PUBLIC_OUTPUT_MODE: "export",
      NEXT_PUBLIC_STATIC_SHELL: undefined,
      NEXT_PUBLIC_SITE_URL: "https://example.org",
      API_BASEPATH: "http://api:8000",
    });
    expect(metadata.title).toBe("問い");
  });
});

describe("[slug] generateMetadata（NEXT_PUBLIC_SITE_URL が不正）", () => {
  it("SSR で URL として読めない値でも例外にせず、既定の metadata を返す", async () => {
    global.fetch = jest.fn(async () => {
      throw new Error("API down");
    }) as unknown as typeof fetch;
    jest.spyOn(console, "error").mockImplementation(() => {});
    const metadata = await generateMetadataWith({
      NEXT_PUBLIC_OUTPUT_MODE: undefined,
      NEXT_PUBLIC_SITE_URL: "not a url",
    });
    expect(metadata.title).toBe("広聴AI");
    expect(metadata.metadataBase).toBeUndefined();
  });
});
