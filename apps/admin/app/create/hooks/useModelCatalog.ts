import { useCallback, useEffect, useState } from "react";

export interface ModelOption {
  value: string;
  label: string;
  description?: string;
  verified?: boolean;
  unverified_label?: string;
  available?: boolean;
  deprecated?: boolean;
  discovery_warning?: string;
  actual_model?: string | null;
  price?: {
    input: number;
    output: number;
    conditions?: string;
    valid_until?: string;
    checked_at?: string | null;
  } | null;
}

export function modelLabel(option: ModelOption): string {
  if (option.deprecated) return `${option.label}（提供終了・再選択してください）`;
  if (option.available === false) return `${option.label}（選択不可・再選択してください）`;
  return option.verified ? option.label : `${option.label}（${option.unverified_label || "動作未検証"}）`;
}

export function modelDescription(option?: ModelOption): string {
  if (!option) return "";
  const price = option.price
    ? `参考単価（100万トークン）：入力 $${option.price.input} / 出力 $${option.price.output}。${option.price.conditions || ""}${option.price.valid_until ? ` 適用期限：${option.price.valid_until}。` : ""}${option.price.checked_at ? ` 確認日：${option.price.checked_at}` : " 単価の最終確認日は不明です。"}`
    : "料金不明";
  return `${option.description || ""}${option.actual_model ? ` 利用モデル：${option.actual_model}。` : ""} ${price}`.trim();
}

/** Both create and duplicate read the server catalog. No model list lives here. */
export function useModelCatalog(provider: string, address?: string, enabled = true) {
  const [state, setState] = useState<{ key: string; models: ModelOption[]; error: string; loading: boolean }>({
    key: "",
    models: [],
    error: "",
    loading: false,
  });
  const [revision, setRevision] = useState(0);
  const key = `${provider}:${address || ""}:${revision}`;
  const reload = useCallback(() => setRevision((value) => value + 1), []);
  useEffect(() => {
    if (!enabled) return;
    let cancelled = false;
    const controller = new AbortController();
    setState({ key, models: [], error: "", loading: true });
    const timer = window.setTimeout(
      async () => {
        try {
          const params = new URLSearchParams({ provider });
          if (provider === "local" && address) params.set("address", address.trim());
          const response = await fetch(`${process.env.NEXT_PUBLIC_API_BASEPATH}/admin/models?${params}`, {
            method: "GET",
            headers: { "x-api-key": process.env.NEXT_PUBLIC_ADMIN_API_KEY || "", "Content-Type": "application/json" },
            signal: controller.signal,
          });
          if (!response.ok) throw new Error(`HTTP ${response.status}`);
          const models: ModelOption[] = await response.json();
          if (!Array.isArray(models)) throw new Error("Invalid catalog");
          if (!cancelled) setState({ key, models, error: "", loading: false });
        } catch {
          if (!cancelled)
            setState({
              key,
              models: [],
              error: "モデル一覧を取得できませんでした。再取得してください。",
              loading: false,
            });
        }
      },
      provider === "local" ? 500 : 0,
    );
    return () => {
      cancelled = true;
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [provider, address, key, enabled]);
  return {
    models: state.key === key ? state.models : [],
    loading: enabled && (state.key !== key || state.loading),
    error: state.key === key ? state.error : "",
    reload,
  };
}
