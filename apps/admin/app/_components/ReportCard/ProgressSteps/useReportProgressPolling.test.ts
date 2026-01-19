import { renderHook, waitFor } from "@testing-library/react";
import { useReportProgressPoll } from "./useReportProgressPolling";

// Mock fetch
global.fetch = jest.fn();

// Mock environment variables
const mockEnv = {
  NEXT_PUBLIC_API_BASEPATH: "http://localhost:8000",
  NEXT_PUBLIC_ADMIN_API_KEY: "test-api-key",
};

Object.defineProperty(process.env, "NEXT_PUBLIC_API_BASEPATH", {
  value: mockEnv.NEXT_PUBLIC_API_BASEPATH,
});
Object.defineProperty(process.env, "NEXT_PUBLIC_ADMIN_API_KEY", {
  value: mockEnv.NEXT_PUBLIC_ADMIN_API_KEY,
});

// Mock timers
jest.useFakeTimers();

describe("useReportProgressPoll", () => {
  const mockFetch = fetch as jest.MockedFunction<typeof fetch>;
  const original = console.error;

  beforeAll(() => {
    console.error = jest.fn();
  });

  beforeEach(() => {
    mockFetch.mockClear();
    jest.clearAllTimers();
  });

  afterEach(() => {
    jest.runOnlyPendingTimers();
    jest.clearAllTimers();
    jest.useRealTimers();
    jest.useFakeTimers();
    jest.resetAllMocks();
  });

  afterAll(() => {
    console.error = original;
  });

  it("初期状態でloadingが設定される", () => {
    const { result } = renderHook(() => useReportProgressPoll("test-slug"));

    expect(result.current.progress).toBe("loading");
  });

  it("正しいヘッダーとURLでAPI呼び出しが行われる", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ current_step: "completed" }),
    } as Response);

    renderHook(() => useReportProgressPoll("test-slug"));

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledWith("http://localhost:8000/admin/reports/test-slug/status/step-json", {
        headers: {
          "x-api-key": "test-api-key",
          "Content-Type": "application/json",
          "Cache-Control": "no-cache, no-store, must-revalidate",
          Pragma: "no-cache",
        },
      });
    });
  });

  it("APIからcurrent_stepが返された時にprogressが更新される", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ current_step: "processing" }),
    } as Response);

    const { result } = renderHook(() => useReportProgressPoll("test-slug"));

    await waitFor(() => {
      expect(result.current.progress).toBe("processing");
    });
  });

  it("current_stepがcompletedの時にポーリングが停止される", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ current_step: "completed" }),
    } as Response);

    const { result } = renderHook(() => useReportProgressPoll("test-slug"));

    await waitFor(() => {
      expect(result.current.progress).toBe("completed");
    });

    // 保留中の呼び出しをクリア
    jest.runAllTimers();

    // 完了後に追加の呼び出しがないことを確認
    expect(mockFetch).toHaveBeenCalledTimes(1);
  });

  it("current_stepがerrorの時にprogressがerrorに設定される", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: async () => ({ current_step: "error" }),
    } as Response);

    const { result } = renderHook(() => useReportProgressPoll("test-slug"));

    await waitFor(() => {
      expect(result.current.progress).toBe("error");
    });
  });

  it("current_stepがloadingまたはnullの時にポーリングが継続される", async () => {
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ current_step: "loading" }),
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ current_step: "processing" }),
      } as Response);

    const { result } = renderHook(() => useReportProgressPoll("test-slug"));

    // 最初の呼び出しでloadingが返される
    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledTimes(1);
    });

    // 次のポーリングをトリガーするために時間を進める
    jest.advanceTimersByTime(3000);

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledTimes(2);
      expect(result.current.progress).toBe("processing");
    });
  });

  it("失敗したリクエストがmaxRetriesまでリトライされる", async () => {
    mockFetch
      .mockRejectedValueOnce(new Error("Network error"))
      .mockRejectedValueOnce(new Error("Network error"))
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ current_step: "processing" }),
      } as Response);

    const { result } = renderHook(() => useReportProgressPoll("test-slug"));

    // 最初の失敗した試行を待つ
    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledTimes(1);
    });

    // 最初のリトライをトリガーするために時間を進める
    jest.advanceTimersByTime(5000);

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledTimes(2);
    });

    // 2回目のリトライをトリガーするために時間を進める
    jest.advanceTimersByTime(5000);

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledTimes(3);
      expect(result.current.progress).toBe("processing");
    });
  });

  it("最大リトライ回数後にエラーが設定される", async () => {
    // maxRetriesより1多い11回の失敗した試行をモック
    for (let i = 0; i < 11; i++) {
      mockFetch.mockResolvedValueOnce({
        ok: false,
        json: async () => ({ current_step: "loading" }),
      } as Response);
    }

    const { result } = renderHook(() => useReportProgressPoll("test-slug"));

    // すべてのリトライ試行を通して時間を進める
    for (let i = 0; i < 10; i++) {
      jest.advanceTimersByTime(5000);
      await waitFor(() => {});
    }

    await waitFor(() => {
      expect(result.current.progress).toBe("loading");
      expect(result.current.isError).toBe(true);
    });
  });

  it("例外による最大リトライ回数後にエラーが設定される", async () => {
    // maxRetriesより1多い11回の失敗した試行をモック
    for (let i = 0; i < 11; i++) {
      mockFetch.mockRejectedValueOnce(new Error("Network error"));
    }

    const { result } = renderHook(() => useReportProgressPoll("test-slug"));

    // すべてのリトライ試行を通して時間を進める
    for (let i = 0; i < 10; i++) {
      jest.advanceTimersByTime(5000);
      await waitFor(() => {});
    }

    await waitFor(() => {
      expect(result.current.progress).toBe("loading");
      expect(result.current.isError).toBe(true);
    });
  });

  it("HTTPエラーレスポンスがリトライロジックで処理される", async () => {
    mockFetch
      .mockResolvedValueOnce({
        ok: false,
        status: 500,
      } as Response)
      .mockResolvedValueOnce({
        ok: false,
        status: 500,
      } as Response)
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ current_step: "processing" }),
      } as Response);

    const { result } = renderHook(() => useReportProgressPoll("test-slug"));

    // 最初の失敗した試行を待つ
    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledTimes(1);
    });

    // 最初のリトライをトリガーするために時間を進める（短い間隔）
    jest.advanceTimersByTime(2000);
    await Promise.resolve();

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledTimes(2);
    });

    // 2回目のリトライをトリガーするために時間を進める（短い間隔）
    jest.advanceTimersByTime(2000);
    await Promise.resolve();

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledTimes(3);
      expect(result.current.progress).toBe("processing");
    });
  });

  it("アンマウント時にクリーンアップが行われる", async () => {
    mockFetch.mockImplementation(
      () =>
        new Promise((resolve) => {
          setTimeout(() => {
            resolve({
              ok: true,
              json: async () => ({ current_step: "processing" }),
            } as Response);
          }, 1000);
        }),
    );

    const { unmount } = renderHook(() => useReportProgressPoll("test-slug"));

    // fetchが完了する前にアンマウント
    unmount();

    // fetch完了を過ぎて時間を進める
    jest.advanceTimersByTime(5000);

    // フックがエラーなしでクリーンアップを適切に処理することを確認
    expect(mockFetch).toHaveBeenCalledTimes(1);
  });
});
