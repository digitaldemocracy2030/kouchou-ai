import { getApiBaseUrl } from "../../../utils/api";
import { reportDelete } from "./reportDelete";

// APIユーティリティ関数をモック化
jest.mock("../../../utils/api", () => ({
  getApiBaseUrl: jest.fn(),
}));

// fetchをモック化
global.fetch = jest.fn();

// window.location.reloadをモック化
const mockReload = jest.fn();
Object.defineProperty(window, "location", {
  value: { reload: mockReload },
  writable: true,
});

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

  it("成功時にDELETEリクエストを送信してページをリロードする", async () => {
    // 成功レスポンスをモック
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
    });

    await reportDelete(mockSlug);

    // 正しいパラメータでfetchが呼ばれることを確認
    expect(fetch).toHaveBeenCalledWith(`${mockApiBaseUrl}/admin/reports/${mockSlug}`, {
      method: "DELETE",
      headers: {
        "x-api-key": mockApiKey,
        "Content-Type": "application/json",
      },
    });

    // ページがリロードされることを確認
    expect(mockReload).toHaveBeenCalledTimes(1);
    expect(mockConsoleError).not.toHaveBeenCalled();
  });

  it("レスポンスがエラーの場合にエラーをログに出力する", async () => {
    const mockErrorDetail = "レポートが見つかりません";

    // エラーレスポンスをモック
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      json: jest.fn().mockResolvedValueOnce({
        detail: mockErrorDetail,
      }),
    });

    await reportDelete(mockSlug);

    // エラーがログに出力されることを確認
    expect(mockConsoleError).toHaveBeenCalledWith(new Error(mockErrorDetail));
    expect(mockReload).not.toHaveBeenCalled();
  });

  it("エラーレスポンスにdetailがない場合にデフォルトメッセージを使用する", async () => {
    // detailなしのエラーレスポンスをモック
    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: false,
      json: jest.fn().mockResolvedValueOnce({}),
    });

    await reportDelete(mockSlug);

    expect(mockConsoleError).toHaveBeenCalledWith(new Error("レポートの削除に失敗しました"));
  });

  it("fetch自体が失敗した場合にエラーをログに出力する", async () => {
    const mockError = new Error("ネットワークエラー");

    // fetchがエラーをスローすることをモック
    (fetch as jest.Mock).mockRejectedValueOnce(mockError);

    await reportDelete(mockSlug);

    expect(mockConsoleError).toHaveBeenCalledWith(mockError);
    expect(mockReload).not.toHaveBeenCalled();
  });

  it("正しいAPIエンドポイントURLを構築する", async () => {
    const customApiUrl = "https://custom-api.example.com";
    (getApiBaseUrl as jest.Mock).mockReturnValue(customApiUrl);

    (fetch as jest.Mock).mockResolvedValueOnce({
      ok: true,
    });

    await reportDelete(mockSlug);

    expect(fetch).toHaveBeenCalledWith(`${customApiUrl}/admin/reports/${mockSlug}`, expect.any(Object));
  });
});
