import { buildCspHeaderValue, extractAllowedOrigins } from "../../../../shared/csp";

describe("CSP helpers", () => {
  it("extracts unique http/https origins and ignores invalid values", () => {
    expect(
      extractAllowedOrigins([
        "http://18.233.19.158:8000/meta/icon.png",
        "https://example.com/api",
        "https://example.com/other",
        "ws://localhost:8000",
        "not-a-url",
        undefined,
      ]),
    ).toEqual(["http://18.233.19.158:8000", "https://example.com"]);
  });

  it("builds a CSP that allows configured API and site origins", () => {
    const csp = buildCspHeaderValue({
      apiBasePath: "http://18.233.19.158:8000",
      publicApiBasePath: "http://18.233.19.158:8000/v1",
      siteUrl: "http://18.233.19.158:4000",
    });

    expect(csp).toContain("img-src 'self' data: blob: http://18.233.19.158:8000 http://18.233.19.158:4000");
    expect(csp).toContain("connect-src 'self' http://18.233.19.158:8000 http://18.233.19.158:4000");
    expect(csp).toContain("style-src 'self' 'unsafe-inline' https://fonts.googleapis.com");
    expect(csp).toContain("font-src 'self' data: https://fonts.gstatic.com");
  });

  it("adds Google Analytics origins only when enabled", () => {
    const withoutGa = buildCspHeaderValue({});
    const withGa = buildCspHeaderValue({ enableGoogleAnalytics: true });

    expect(withoutGa).not.toContain("https://www.googletagmanager.com");
    expect(withGa).toContain("script-src 'self' 'unsafe-inline' https://www.googletagmanager.com");
    expect(withGa).toContain("connect-src 'self' https://www.googletagmanager.com https://www.google-analytics.com");
  });
});
