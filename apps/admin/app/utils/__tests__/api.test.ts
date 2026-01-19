import { getApiBaseUrl } from "../api";

describe("getApiBaseUrl", () => {
  const originalEnv = process.env;

  beforeEach(() => {
    jest.resetModules();
    process.env = { ...originalEnv };
  });

  afterEach(() => {
    process.env = originalEnv;
  });

  it("returns NEXT_PUBLIC_API_BASEPATH when window is defined", () => {
    Object.defineProperty(global, "window", {
      value: {},
      writable: true,
    });

    process.env.NEXT_PUBLIC_API_BASEPATH = "https://example.com/api";

    expect(getApiBaseUrl()).toBe("https://example.com/api");
  });

  it("returns API_BASEPATH when window is undefined and API_BASEPATH is defined", () => {
    Object.defineProperty(global, "window", {
      value: undefined,
      writable: true,
    });

    process.env.API_BASEPATH = "https://server-side.com/api";
    process.env.NEXT_PUBLIC_API_BASEPATH = "https://example.com/api";

    expect(getApiBaseUrl()).toBe("https://server-side.com/api");
  });

  it("returns NEXT_PUBLIC_API_BASEPATH when window is undefined and API_BASEPATH is not defined", () => {
    Object.defineProperty(global, "window", {
      value: undefined,
      writable: true,
    });

    process.env.API_BASEPATH = undefined;
    process.env.NEXT_PUBLIC_API_BASEPATH = "https://example.com/api";

    expect(getApiBaseUrl()).toBe("https://example.com/api");
  });
});
