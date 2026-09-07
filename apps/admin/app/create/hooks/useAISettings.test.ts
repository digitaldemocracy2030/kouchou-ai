import { act, renderHook, waitFor } from "@testing-library/react";
import { useAISettings } from "./useAISettings";

const serverCatalog = require("../../../../api/src/services/model_catalog.json");
beforeEach(() => {
  window.localStorage.clear();
  global.fetch = jest.fn(async (url) => {
    const provider = new URL(String(url), "http://localhost").searchParams.get("provider");
    return {
      ok: true,
      json: async () =>
        provider === "local"
          ? [{ value: "llama3", label: "Llama 3", available: true, verified: false }]
          : serverCatalog.filter((row: { provider: string }) => row.provider === provider),
    } as Response;
  });
});

it("保存済みの提供終了モデルを置換せず再選択を求める", async () => {
  window.localStorage.setItem("kouchou_ai_provider", JSON.stringify("gemini"));
  window.localStorage.setItem("kouchou_ai_model", JSON.stringify("gemini-1.5-pro"));
  const { result } = renderHook(() => useAISettings());
  await waitFor(() => expect(result.current.modelError).toContain("再選択"));
  expect(result.current.model).toBe("gemini-1.5-pro");
  act(() =>
    result.current.handleModelChange({ target: { value: "gemini-3.8-flash" } } as React.ChangeEvent<HTMLSelectElement>),
  );
  expect(result.current.modelError).toBe("");
});

it("未検証モデルを保存して再読込しても選択可能", async () => {
  window.localStorage.setItem("kouchou_ai_model", JSON.stringify("gpt-5.6-terra"));
  const { result } = renderHook(() => useAISettings());
  await waitFor(() => expect(result.current.modelError).toBe(""));
  expect(result.current.model).toBe("gpt-5.6-terra");
  expect(result.current.getCurrentModels().find((m) => m.value === result.current.model)?.verified).toBe(false);
});

it("LocalLLMを自動取得し、接続先変更時は古い選択を勝手に置換しない", async () => {
  const { result } = renderHook(() => useAISettings());
  act(() =>
    result.current.handleProviderChange({ target: { value: "local" } } as React.ChangeEvent<HTMLSelectElement>),
  );
  await waitFor(() => expect(result.current.model).toBe("llama3"));
  expect(result.current.isEmbeddedAtLocal).toBe(true);
  (global.fetch as jest.Mock).mockResolvedValue({
    ok: true,
    json: async () => [{ value: "other", label: "Other", available: true }],
  });
  act(() => result.current.setLocalLLMAddress("new-host:1234"));
  await waitFor(() => expect(result.current.getCurrentModels().some((m) => m.value === "other")).toBe(true));
  expect(result.current.model).toBe("llama3");
  expect(result.current.modelError).toContain("再選択");
});

it("一覧取得失敗を表示し再取得できる", async () => {
  (global.fetch as jest.Mock).mockRejectedValueOnce(new Error("offline"));
  const { result } = renderHook(() => useAISettings());
  await waitFor(() => expect(result.current.modelError).toContain("取得できません"));
  act(() => result.current.reloadModels());
  await waitFor(() => expect(result.current.modelError).toBe(""));
});
