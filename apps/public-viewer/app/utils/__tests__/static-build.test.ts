import type { Report } from "@/type";
import { createStaticBuildFetchError, getStaticBuildReportSlugs, parseBuildSlugs } from "../static-build";

const readyReport = (slug: string): Report => ({
  slug,
  status: "ready",
  title: `${slug} title`,
  description: `${slug} description`,
  isPubcom: false,
  visibility: "public" as Report["visibility"],
});

describe("static build helpers", () => {
  const originalEnv = process.env;

  beforeEach(() => {
    process.env = { ...originalEnv };
  });

  afterEach(() => {
    process.env = originalEnv;
  });

  it("returns ready report slugs", () => {
    const result = getStaticBuildReportSlugs([readyReport("alpha"), { ...readyReport("draft"), status: "draft" }]);

    expect(result).toEqual([{ slug: "alpha" }]);
  });

  it("filters by BUILD_SLUGS when matching ready reports exist", () => {
    const result = getStaticBuildReportSlugs([readyReport("alpha"), readyReport("beta")], "beta");

    expect(result).toEqual([{ slug: "beta" }]);
  });

  it("throws a clear error when no ready reports exist during static export", () => {
    process.env.NEXT_PUBLIC_OUTPUT_MODE = "export";

    expect(() => getStaticBuildReportSlugs([{ ...readyReport("draft"), status: "draft" }])).toThrow(
      "静的HTML出力に必要な公開状態のレポートが見つかりませんでした。",
    );
  });

  it("throws a distinct error when BUILD_SLUGS does not match any ready report during static export", () => {
    process.env.NEXT_PUBLIC_OUTPUT_MODE = "export";

    expect(() => getStaticBuildReportSlugs([readyReport("alpha")], "missing")).toThrow(
      'BUILD_SLUGS で指定されたレポートが、公開状態（status: ready）の一覧に見つかりませんでした。 指定値: "missing" 公開状態の slug: "alpha"',
    );
  });

  it("parses BUILD_SLUGS with trimming and empty entries removed", () => {
    expect(parseBuildSlugs(" alpha, ,beta ,, gamma ")).toEqual(["alpha", "beta", "gamma"]);
  });

  it("formats fetch errors with troubleshooting guidance", () => {
    expect(createStaticBuildFetchError(new Error("connect ECONNREFUSED"))).toThrow;

    const error = createStaticBuildFetchError(new Error("connect ECONNREFUSED"));
    expect(error.message).toContain("静的HTML出力の事前確認でレポート一覧の取得に失敗しました。");
    expect(error.message).toContain("元エラー: connect ECONNREFUSED");
  });
});
