import { fetchShellJson, getShellMetaUrl, getShellReportUrl, resolveShellSlug } from "../shell-data";
import { isStaticShellBuild } from "../static-build";

describe("resolveShellSlug", () => {
  it("reads the slug from a trailing-slash path", () => {
    expect(resolveShellSlug("/example/")).toBe("example");
  });

  it("reads the slug when index.html is explicit", () => {
    expect(resolveShellSlug("/example/index.html")).toBe("example");
  });

  it("returns null at the site root", () => {
    expect(resolveShellSlug("/")).toBeNull();
    expect(resolveShellSlug("/index.html")).toBeNull();
  });

  it("strips the base path", () => {
    expect(resolveShellSlug("/base/example/", "/base")).toBe("example");
    expect(resolveShellSlug("/base/example/index.html", "/base/")).toBe("example");
    expect(resolveShellSlug("/base/", "/base")).toBeNull();
  });

  it("does not strip a base path that only shares a prefix", () => {
    // "/basement" は "/base" 配下ではない
    expect(resolveShellSlug("/basement/example/", "/base")).toBe("basement");
  });
});

describe("shell data urls", () => {
  const originalEnv = process.env;

  beforeEach(() => {
    process.env = { ...originalEnv };
  });

  afterEach(() => {
    process.env = originalEnv;
  });

  it("uses the export base path", () => {
    process.env.NEXT_PUBLIC_OUTPUT_MODE = "export";
    process.env.NEXT_PUBLIC_STATIC_EXPORT_BASE_PATH = "/base";

    expect(getShellMetaUrl()).toBe("/base/data/metadata.json");
    expect(getShellReportUrl("example")).toBe("/base/data/reports/example.json");
  });

  it("falls back to an absolute path without a base path", () => {
    process.env.NEXT_PUBLIC_OUTPUT_MODE = "export";
    process.env.NEXT_PUBLIC_STATIC_EXPORT_BASE_PATH = "";

    expect(getShellReportUrl("example")).toBe("/data/reports/example.json");
  });

  it("encodes the slug", () => {
    process.env.NEXT_PUBLIC_OUTPUT_MODE = "export";
    process.env.NEXT_PUBLIC_STATIC_EXPORT_BASE_PATH = "";

    expect(getShellReportUrl("a b/c")).toBe("/data/reports/a%20b%2Fc.json");
  });
});

describe("isStaticShellBuild", () => {
  const originalEnv = process.env;

  beforeEach(() => {
    process.env = { ...originalEnv };
  });

  afterEach(() => {
    process.env = originalEnv;
  });

  it("is true only when the export build opts in", () => {
    process.env.NEXT_PUBLIC_OUTPUT_MODE = "export";
    process.env.NEXT_PUBLIC_STATIC_SHELL = "1";
    expect(isStaticShellBuild()).toBe(true);
  });

  it("is false for a plain static export", () => {
    process.env.NEXT_PUBLIC_OUTPUT_MODE = "export";
    delete process.env.NEXT_PUBLIC_STATIC_SHELL;
    expect(isStaticShellBuild()).toBe(false);
  });

  it("is false outside the export build", () => {
    delete process.env.NEXT_PUBLIC_OUTPUT_MODE;
    process.env.NEXT_PUBLIC_STATIC_SHELL = "1";
    expect(isStaticShellBuild()).toBe(false);
  });
});

describe("fetchShellJson", () => {
  const originalFetch = global.fetch;

  afterEach(() => {
    global.fetch = originalFetch;
  });

  it("returns the parsed body", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ slug: "example" }),
    }) as unknown as typeof fetch;

    await expect(fetchShellJson<{ slug: string }>("/data/reports/example.json")).resolves.toEqual({
      slug: "example",
    });
  });

  it("returns null on 404 so the caller can show not-found", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      status: 404,
      statusText: "Not Found",
    }) as unknown as typeof fetch;

    await expect(fetchShellJson("/data/reports/missing.json")).resolves.toBeNull();
  });

  it("throws on other failures", async () => {
    global.fetch = jest.fn().mockResolvedValue({
      ok: false,
      status: 500,
      statusText: "Internal Server Error",
    }) as unknown as typeof fetch;

    await expect(fetchShellJson("/data/reports/example.json")).rejects.toThrow("500");
  });
});
