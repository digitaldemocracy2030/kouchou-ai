import { verifyApiKey } from "./verifyApiKey";

// APIレスポンスをモック
global.fetch = jest.fn();

// getApiBaseUrl関数をモック
jest.mock("@/app/utils/api", () => ({
  getApiBaseUrl: jest.fn(() => "http://localhost:8000"),
}));

describe("verifyApiKey", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    // 環境変数をモック
    process.env.NEXT_PUBLIC_ADMIN_API_KEY = "test-api-key";
  });

  afterEach(() => {
    process.env.NEXT_PUBLIC_ADMIN_API_KEY = undefined;
  });

  it("API検証が成功した場合、正常な結果を返すべき", async () => {
    const mockResponse = {
      success: true,
      message: "API key verified successfully",
      available_models: ["gpt-3.5-turbo", "gpt-4"],
    };

    (fetch as jest.Mock).mockResolvedValueOnce({
      json: jest.fn().mockResolvedValueOnce(mockResponse),
    });

    const result = await verifyApiKey("openai");

    expect(fetch).toHaveBeenCalledWith(
      "http://localhost:8000/admin/environment/verify?provider=openai",
      {
        method: "GET",
        headers: {
          "x-api-key": "test-api-key",
          "Content-Type": "application/json",
        },
      },
    );

    expect(result).toEqual({
      result: mockResponse,
      error: false,
    });
  });

  it("ネットワークエラーが発生した場合、エラー状態を返すべき", async () => {
    (fetch as jest.Mock).mockRejectedValueOnce(new Error("Network error"));

    const consoleSpy = jest.spyOn(console, "error").mockImplementation(() => {});

    const result = await verifyApiKey("openai");

    expect(result).toEqual({
      result: null,
      error: true,
    });

    expect(consoleSpy).toHaveBeenCalledWith("Error verifying API key:", expect.any(Error));

    consoleSpy.mockRestore();
  });

  it("指定したプロバイダーに応じたURLでAPIを呼び出すべき", async () => {
    const mockResponse = {
      success: true,
      message: "API key verified successfully",
    };

    (fetch as jest.Mock).mockResolvedValueOnce({
      json: jest.fn().mockResolvedValueOnce(mockResponse),
    });

    await verifyApiKey("gemini");

    expect(fetch).toHaveBeenCalledWith(
      "http://localhost:8000/admin/environment/verify?provider=gemini",
      expect.any(Object),
    );
  });
});
