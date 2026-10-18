/**
 * @jest-environment node
 */
import { fetchApiWithRetry, fetchFont } from "../_op-image";

jest.mock("next/og", () => ({ ImageResponse: jest.fn() }));

const fetchMock = jest.fn();

beforeEach(() => {
  fetchMock.mockReset();
  global.fetch = fetchMock as unknown as typeof fetch;
  jest.spyOn(console, "warn").mockImplementation(() => {});
});

afterEach(() => {
  jest.restoreAllMocks();
});

describe("fetchFont", () => {
  it("一度失敗しても失敗した Promise をキャッシュせず、次の呼び出しで取り直す", async () => {
    fetchMock.mockRejectedValueOnce(new TypeError("fetch failed"));
    await expect(fetchFont(400)).rejects.toThrow("fetch failed");

    const font = new ArrayBuffer(8);
    fetchMock
      .mockResolvedValueOnce(new Response("src: url(https://fonts.example/a.woff2) format('woff2');"))
      .mockResolvedValueOnce(new Response(font));
    await expect(fetchFont(400)).resolves.toBeInstanceOf(ArrayBuffer);
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });

  it("フォント CSS の取得が非 2xx なら失敗として扱う", async () => {
    fetchMock.mockResolvedValueOnce(new Response("url(https://fonts.example/err.woff2)", { status: 503 }));
    await expect(fetchFont(700)).rejects.toThrow("503");
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });
});

describe("fetchApiWithRetry", () => {
  it("4xx はリトライせずに 1 回で失敗する", async () => {
    fetchMock.mockResolvedValue(new Response("not found", { status: 404 }));
    await expect(fetchApiWithRetry("http://api/reports/x", {}, 5, 0)).rejects.toThrow("404");
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("5xx はリトライして、成功した応答を返す", async () => {
    fetchMock
      .mockResolvedValueOnce(new Response("error", { status: 503 }))
      .mockResolvedValueOnce(new Response("{}", { status: 200 }));
    const response = await fetchApiWithRetry("http://api/reports/x", {}, 5, 0);
    expect(response.status).toBe(200);
    expect(fetchMock).toHaveBeenCalledTimes(2);
  });

  it("ネットワークエラーはリトライし、最後の試行で投げ直す", async () => {
    fetchMock.mockRejectedValue(new TypeError("fetch failed"));
    await expect(fetchApiWithRetry("http://api/reports/x", {}, 2, 0)).rejects.toThrow("fetch failed");
    expect(fetchMock).toHaveBeenCalledTimes(3);
  });
});
