import { duplicateReport } from "./actions";

jest.mock("@/app/utils/api", () => ({
  getApiBaseUrl: () => "http://localhost:8000",
}));

const mockFetch = jest.fn();
global.fetch = mockFetch;

describe("duplicateReport", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    process.env.ADMIN_API_KEY = "admin-key";
    mockFetch.mockResolvedValue({
      ok: true,
      json: jest.fn().mockResolvedValue({ report: { slug: "new-slug" } }),
    });
  });

  it("ユーザー API キーがある場合は x-user-api-key ヘッダーで送る", async () => {
    const result = await duplicateReport("source", { reuseEnabled: true, userApiKey: "user-key" });

    expect(result).toEqual({ success: true, slug: "new-slug" });
    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/admin/reports/source/duplicate",
      expect.objectContaining({
        method: "POST",
        // 鍵を載せた要求をリダイレクト先へ転送しない
        redirect: "error",
        headers: {
          "x-api-key": "admin-key",
          "Content-Type": "application/json",
          "x-user-api-key": "user-key",
        },
      }),
    );
    // キーは本文には入れない
    const body = JSON.parse(mockFetch.mock.calls[0][1].body);
    expect(body).toEqual({ reuse: { enabled: true } });
  });

  it("ユーザー API キーが無い場合は x-user-api-key ヘッダーを付けない", async () => {
    await duplicateReport("source", { reuseEnabled: false });

    expect(mockFetch.mock.calls[0][1].headers).toEqual({
      "x-api-key": "admin-key",
      "Content-Type": "application/json",
    });
  });
});
