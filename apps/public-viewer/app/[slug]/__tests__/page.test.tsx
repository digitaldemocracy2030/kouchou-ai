/**
 * @jest-environment node
 */
import { ReportVisibility } from "@/type";

jest.mock("@/components/report/ReportShell", () => ({ ReportShell: () => null }));
jest.mock("@/components/report/ReportView", () => ({ ReportView: () => null }));
jest.mock("@/components/reporter/Reporter", () => ({ Reporter: () => null }));
jest.mock("next/navigation", () => ({
  notFound: () => {
    throw new Error("NEXT_NOT_FOUND");
  },
}));

import Page, { generateMetadata } from "../page";

const meta = { reporter: "テスト報告者" };

const makeResult = (visibility: ReportVisibility) => ({
  config: { question: "テストの問い" },
  overview: "概要",
  visibility,
});

const jsonResponse = (body: unknown, status = 200) =>
  ({ ok: status >= 200 && status < 300, status, json: async () => body }) as Response;

const mockFetch = (result: unknown, resultStatus = 200) => {
  global.fetch = jest.fn(async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url.endsWith("/meta/metadata.json")) {
      return jsonResponse(meta);
    }
    return jsonResponse(result, resultStatus);
  }) as typeof fetch;
};

const params = Promise.resolve({ slug: "test-slug" });

describe("[slug] page (SSR / ISR)", () => {
  const originalEnv = { ...process.env };
  const originalFetch = global.fetch;

  beforeEach(() => {
    process.env = { ...originalEnv, API_BASEPATH: "http://api:8000" };
    process.env.NEXT_PUBLIC_OUTPUT_MODE = undefined;
    process.env.NEXT_PUBLIC_STATIC_SHELL = undefined;
  });

  afterEach(() => {
    process.env = originalEnv;
    global.fetch = originalFetch;
  });

  describe("generateMetadata", () => {
    it("限定公開レポートには noindex, nofollow を付ける", async () => {
      mockFetch(makeResult(ReportVisibility.UNLISTED));
      const metadata = await generateMetadata({ params });
      expect(metadata.robots).toEqual({ index: false, follow: false });
    });

    it("公開レポートには noindex を付けない", async () => {
      mockFetch(makeResult(ReportVisibility.PUBLIC));
      const metadata = await generateMetadata({ params });
      expect(metadata.robots).toBeUndefined();
      expect(metadata.title).toBe("テストの問い - テスト報告者");
    });

    it("API に届かない場合は既定のタイトルにフォールバックする", async () => {
      global.fetch = jest.fn(async () => {
        throw new TypeError("fetch failed");
      }) as typeof fetch;
      const metadata = await generateMetadata({ params });
      expect(metadata).toEqual({ title: "広聴AI" });
    });
  });

  describe("Page", () => {
    it("API 接続エラーを正常な描画として返さず throw する（ISR に失敗結果をキャッシュさせない）", async () => {
      global.fetch = jest.fn(async () => {
        throw new TypeError("fetch failed");
      }) as typeof fetch;
      await expect(Page({ params })).rejects.toThrow();
    });
  });
});
