import { getApiBaseUrl } from "../../../utils/api";
import { csvDownload } from "./csvDownload";

// Mock API関数
jest.mock("../../../utils/api", () => ({
  getApiBaseUrl: jest.fn(),
}));

const mockGetApiBaseUrl = getApiBaseUrl as jest.MockedFunction<typeof getApiBaseUrl>;

describe("csvDownload", () => {
  beforeEach(() => {
    // fetchのモック
    global.fetch = jest.fn();

    // APIベースURLのモック
    mockGetApiBaseUrl.mockReturnValue("http://localhost:8000");

    // 環境変数のモック
    process.env.NEXT_PUBLIC_ADMIN_API_KEY = "test-api-key";
  });

  afterEach(() => {
    jest.clearAllMocks();
  });

  it("CSVダウンロードが正常に実行され、適切なデータを返す", async () => {
    const mockData = "test,data\n1,2";
    const mockArrayBuffer = Buffer.from(mockData).buffer;
    const mockBlob = {
      arrayBuffer: jest.fn().mockResolvedValue(mockArrayBuffer),
    };

    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
      blob: () => Promise.resolve(mockBlob),
    });

    const result = await csvDownload("test-slug");

    expect(global.fetch).toHaveBeenCalledWith("http://localhost:8000/admin/comments/test-slug/csv", {
      headers: {
        "x-api-key": "test-api-key",
        "Content-Type": "application/json",
      },
    });

    expect(result).toEqual({
      success: true,
      data: expect.any(String),
      filename: "kouchou_test-slug.csv",
      contentType: "text/csv",
    });

    // Base64エンコードされた文字列であることを確認
    if (result.success) {
      expect(result.data).toMatch(/^[A-Za-z0-9+/]*={0,2}$/);
    }
    expect(mockBlob.arrayBuffer).toHaveBeenCalled();
  });

  it("APIエラーの場合、適切にエラーレスポンスを返す", async () => {
    const errorDetail = "データが見つかりません";

    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      json: () => Promise.resolve({ detail: errorDetail }),
    });

    const result = await csvDownload("test-slug");
    expect(result).toEqual({
      success: false,
      error: errorDetail,
    });
  });

  it("APIエラーでdetailが無い場合、デフォルトエラーメッセージを返す", async () => {
    (global.fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      json: () => Promise.resolve({}),
    });

    const result = await csvDownload("test-slug");
    expect(result).toEqual({
      success: false,
      error: "CSV ダウンロードに失敗しました",
    });
  });

  it("ネットワークエラーの場合、適切にエラーレスポンスを返す", async () => {
    const networkError = new Error("Network error");

    (global.fetch as jest.Mock).mockRejectedValueOnce(networkError);

    const result = await csvDownload("test-slug");
    expect(result).toEqual({
      success: false,
      error: "Network error",
    });
  });
});
