import { getApiBaseUrl } from "../../../utils/api";
import { reportDelete } from "./action";

// APIユーティリティ関数をモック化
jest.mock("../../../utils/api", () => ({
  getApiBaseUrl: jest.fn(),
}));

// fetchをモック化
global.fetch = jest.fn();

// console.errorをモック化してスパイ
const mockConsoleError = jest.spyOn(console, "error").mockImplementation(() => {});

describe("reportDelete", () => {
  const mockSlug = "test-report-slug";
  const mockApiBaseUrl = "https://api.example.com";
  const mockApiKey = "test-api-key";

  beforeEach(() => {
    // 各テスト前にモックをリセット
    jest.clearAllMocks();
    (getApiBaseUrl as jest.Mock).mockReturnValue(mockApiBaseUrl);
    process.env.NEXT_PUBLIC_ADMIN_API_KEY = mockApiKey;
  });

  afterEach(() => {
    // 環境変数をクリア
    process.env.NEXT_PUBLIC_ADMIN_API_KEY = undefined;
  });

  it("成功時にDELETEリクエストを送信してsuccess:trueを返す", async () => {
    // 成功レスポンスをモック
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
    });

    const result = await reportDelete(mockSlug);

    // 正しいパラメータでfetchが呼ばれることを確認
    expect(fetch).toHaveBeenCalledWith(`${mockApiBaseUrl}/admin/reports/${mockSlug}`, {
      method: "DELETE",
      headers: {
        "x-api-key": mockApiKey,
        "Content-Type": "application/json",
      },
    });

    expect(result).toEqual({ success: true });
    expect(mockConsoleError).not.toHaveBeenCalled();
  });

  it("レスポンスがエラーの場合にエラーをログに出力してsuccess:falseを返す", async () => {
    const mockErrorDetail = "レポートが見つかりません";

    // エラーレスポンスをモック
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      json: jest.fn().mockResolvedValueOnce({
        detail: mockErrorDetail,
      }),
    });

    const result = await reportDelete(mockSlug);

    // エラー結果が返されることを確認
    expect(result).toEqual({ success: false, error: mockErrorDetail });
    // エラーがログに出力されることを確認
    expect(mockConsoleError).toHaveBeenCalledWith(new Error(mockErrorDetail));
  });

  it("エラーレスポンスにdetailがない場合にデフォルトメッセージでsuccess:falseを返す", async () => {
    // detailなしのエラーレスポンスをモック
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      json: jest.fn().mockResolvedValueOnce({}),
    });

    const result = await reportDelete(mockSlug);

    expect(result).toEqual({ success: false, error: "レポートの削除に失敗しました" });
    expect(mockConsoleError).toHaveBeenCalledWith(new Error("レポートの削除に失敗しました"));
  });

  it("fetch自体が失敗した場合にエラーをログに出力してsuccess:falseを返す", async () => {
    const mockError = new Error("ネットワークエラー");

    // fetchがエラーをスローすることをモック
    (fetch as jest.Mock).mockRejectedValueOnce(mockError);

    const result = await reportDelete(mockSlug);

    expect(result).toEqual({ success: false, error: "ネットワークエラー" });
    expect(mockConsoleError).toHaveBeenCalledWith(mockError);
  });

  it("正しいAPIエンドポイントURLを構築する", async () => {
    const customApiUrl = "https://custom-api.example.com";
    (getApiBaseUrl as jest.Mock).mockReturnValue(customApiUrl);

    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
    });

    const result = await reportDelete(mockSlug);

    expect(fetch).toHaveBeenCalledWith(`${customApiUrl}/admin/reports/${mockSlug}`, expect.any(Object));
    expect(result).toEqual({ success: true });
  });
});
