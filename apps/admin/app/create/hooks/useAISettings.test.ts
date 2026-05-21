import { toaster } from "@/components/ui/toaster";
import { act, renderHook, waitFor } from "@testing-library/react";
import { useAISettings } from "./useAISettings";

jest.mock("@/components/ui/toaster", () => ({
  toaster: {
    create: jest.fn(),
  },
}));

global.fetch = jest.fn();

const mockFetch = global.fetch as jest.MockedFunction<typeof fetch>;
const mockToasterCreate = toaster.create as jest.MockedFunction<typeof toaster.create>;
const originalEnv = process.env;

describe("useAISettings", () => {
  beforeEach(() => {
    jest.useFakeTimers();
    jest.clearAllMocks();
    window.localStorage.clear();
    process.env = {
      ...originalEnv,
      NEXT_PUBLIC_API_BASEPATH: "http://localhost:8000",
      NEXT_PUBLIC_ADMIN_API_KEY: "test-api-key",
    };
  });

  afterEach(() => {
    jest.clearAllTimers();
    jest.useRealTimers();
    process.env = originalEnv;
  });

  it("LocalLLMを選択するとモデル一覧を自動取得する", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: jest.fn().mockResolvedValueOnce([
        { value: "llama3.1", label: "Llama 3.1" },
        { value: "gemma3", label: "Gemma 3" },
      ]),
    } as unknown as Response);

    const { result } = renderHook(() => useAISettings());

    act(() => {
      result.current.handleProviderChange({ target: { value: "local" } } as React.ChangeEvent<HTMLSelectElement>);
    });

    act(() => {
      jest.advanceTimersByTime(500);
    });

    await waitFor(() => {
      expect(result.current.getCurrentModels()).toHaveLength(2);
    });

    expect(result.current.model).toBe("llama3.1");
    expect(mockFetch).toHaveBeenCalledWith("http://localhost:8000/admin/models?provider=local&address=ollama%3A11434", {
      method: "GET",
      headers: {
        "x-api-key": "test-api-key",
        "Content-Type": "application/json",
      },
    });
    expect(mockToasterCreate).not.toHaveBeenCalled();
  });

  it("LocalLLMアドレス変更後は debounce して自動再取得する", async () => {
    mockFetch
      .mockResolvedValueOnce({
        ok: true,
        json: jest.fn().mockResolvedValueOnce([{ value: "llama3.1", label: "Llama 3.1" }]),
      } as unknown as Response)
      .mockResolvedValueOnce({
        ok: true,
        json: jest.fn().mockResolvedValueOnce([{ value: "mistral", label: "Mistral" }]),
      } as unknown as Response);

    const { result } = renderHook(() => useAISettings());

    act(() => {
      result.current.handleProviderChange({ target: { value: "local" } } as React.ChangeEvent<HTMLSelectElement>);
      jest.advanceTimersByTime(500);
    });

    await waitFor(() => {
      expect(result.current.getCurrentModels()).toHaveLength(1);
    });

    act(() => {
      result.current.setLocalLLMAddress("lmstudio:1234");
      jest.advanceTimersByTime(499);
    });

    expect(mockFetch).toHaveBeenCalledTimes(1);

    act(() => {
      jest.advanceTimersByTime(1);
    });

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalledTimes(2);
    });

    expect(mockFetch).toHaveBeenLastCalledWith(
      "http://localhost:8000/admin/models?provider=local&address=lmstudio%3A1234",
      {
        method: "GET",
        headers: {
          "x-api-key": "test-api-key",
          "Content-Type": "application/json",
        },
      },
    );
    expect(result.current.model).toBe("mistral");
  });

  it("手動取得では toaster を出して再試行できる", async () => {
    mockFetch.mockResolvedValueOnce({
      ok: true,
      json: jest.fn().mockResolvedValueOnce([{ value: "llama3.1", label: "Llama 3.1" }]),
    } as unknown as Response);

    const { result } = renderHook(() => useAISettings());

    act(() => {
      result.current.handleProviderChange({ target: { value: "local" } } as React.ChangeEvent<HTMLSelectElement>);
      result.current.setLocalLLMAddress("lmstudio:1234");
    });

    let fetched = false;
    await act(async () => {
      fetched = await result.current.fetchLocalLLMModels();
    });

    expect(fetched).toBe(true);
    expect(mockToasterCreate).toHaveBeenCalledWith({
      type: "success",
      title: "モデルリスト取得成功",
      description: "1個のモデルを取得しました",
    });
    expect(mockFetch).toHaveBeenCalledWith(
      "http://localhost:8000/admin/models?provider=local&address=lmstudio%3A1234",
      {
        method: "GET",
        headers: {
          "x-api-key": "test-api-key",
          "Content-Type": "application/json",
        },
      },
    );
  });
});
