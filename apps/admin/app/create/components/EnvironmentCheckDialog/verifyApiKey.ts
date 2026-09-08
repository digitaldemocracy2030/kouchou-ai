"use server";

import { getApiBaseUrl } from "@/app/utils/api";

type ErrorType = "authentication_error" | "insufficient_quota" | "rate_limit_error" | "unknown_error";

type VerificationResult = {
  success: boolean;
  message: string;
  available_models?: string[];
  error_type?: ErrorType;
  error_detail?: string;
};

export const verifyApiKey = async (provider: string, userApiKey?: string, model?: string, localLLMAddress?: string) => {
  try {
    const params = new URLSearchParams({ provider });
    if (model?.trim()) params.set("model", model.trim());
    if (provider === "local" && localLLMAddress?.trim()) params.set("local_llm_address", localLLMAddress.trim());
    const headers: Record<string, string> = {
      "x-api-key": process.env.NEXT_PUBLIC_ADMIN_API_KEY || "",
      "Content-Type": "application/json",
    };

    if (userApiKey) {
      headers["x-user-api-key"] = userApiKey;
    }

    const response = await fetch(`${getApiBaseUrl()}/admin/environment/verify?${params}`, {
      method: "GET",
      cache: "no-store",
      headers,
    });

    const result = (await response.json()) as VerificationResult;
    return {
      result,
      error: !response.ok || !result.success || !!result.error_type,
    };
  } catch (error) {
    console.error("Error verifying API key:", error);
    return {
      result: null,
      error: true,
    };
  }
};

export const verifyChatGptApiKeyWithProvider = async (provider = "openai") => {
  try {
    const encodedProvider = encodeURIComponent(provider);
    const response = await fetch(`${getApiBaseUrl()}/admin/environment/verify-chatgpt?provider=${encodedProvider}`, {
      method: "GET",
      headers: {
        "x-api-key": process.env.NEXT_PUBLIC_ADMIN_API_KEY || "",
        "Content-Type": "application/json",
      },
    });

    const result = (await response.json()) as VerificationResult;
    return {
      result,
      error: !!result.error_type,
    };
  } catch (error) {
    console.error("Error verifying API key:", error);
    return {
      result: null,
      error: true,
    };
  }
};
