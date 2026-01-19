import { ReportVisibility } from "@/type";
import { updateReportVisibility } from "./actions";

// Mock getApiBaseUrl
jest.mock("../../../utils/api", () => ({
  getApiBaseUrl: () => "http://localhost:8000",
}));

// Mock console.error to avoid noise in tests
const mockConsoleError = jest.spyOn(console, "error").mockImplementation(() => {});

// Mock fetch
const mockFetch = jest.fn();
global.fetch = mockFetch;

describe("updateReportVisibility", () => {
  beforeEach(() => {
    jest.clearAllMocks();
    process.env.NEXT_PUBLIC_ADMIN_API_KEY = "test-api-key";
  });

  afterAll(() => {
    mockConsoleError.mockRestore();
  });

  it("公開状態の更新が正常に動作する", async () => {
    const mockResponse = {
      ok: true,
      json: jest.fn().mockResolvedValue({ visibility: "public" }),
    };
    mockFetch.mockResolvedValue(mockResponse);

    const result = await updateReportVisibility("test-report-1", ReportVisibility.PUBLIC);

    expect(mockFetch).toHaveBeenCalledWith("http://localhost:8000/admin/reports/test-report-1/visibility", {
      method: "PATCH",
      headers: {
        "x-api-key": "test-api-key",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ visibility: "public" }),
    });

    expect(result).toEqual({
      success: true,
      visibility: "public",
    });
  });

  it("APIエラーレスポンスを適切に処理する", async () => {
    const mockResponse = {
      ok: false,
      json: jest.fn().mockResolvedValue({ detail: "Custom error message" }),
    };
    mockFetch.mockResolvedValue(mockResponse);

    const result = await updateReportVisibility("test-report-1", ReportVisibility.PUBLIC);

    expect(mockConsoleError).toHaveBeenCalledWith(new Error("Custom error message"));
    expect(result).toEqual({
      success: false,
      error: "Custom error message",
    });
  });

  it("詳細メッセージのないAPIエラーを適切に処理する", async () => {
    const mockResponse = {
      ok: false,
      json: jest.fn().mockResolvedValue({}),
    };
    mockFetch.mockResolvedValue(mockResponse);

    const result = await updateReportVisibility("test-report-1", ReportVisibility.PUBLIC);

    expect(mockConsoleError).toHaveBeenCalledWith(new Error("公開状態の変更に失敗しました"));
    expect(result).toEqual({
      success: false,
      error: "公開状態の変更に失敗しました",
    });
  });

  it("ネットワークエラーを適切に処理する", async () => {
    const mockError = new Error("Network error");
    mockFetch.mockRejectedValue(mockError);

    const result = await updateReportVisibility("test-report-1", ReportVisibility.PUBLIC);

    expect(mockConsoleError).toHaveBeenCalledWith(mockError);
    expect(result).toEqual({
      success: false,
      error: "Network error",
    });
  });
});
