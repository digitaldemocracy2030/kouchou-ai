import { NextResponse } from "next/server";

// Per-request fixtures: no shared state and no connection to an LLM provider.
// These sentinel keys are only recognized by the E2E dummy server.
export function GET(request: Request) {
  if (process.env.E2E_TEST === "true") {
    const scenario = request.headers.get("x-user-api-key");
    const errors: Record<string, string> = {
      "e2e-authentication-error": "authentication_error",
      "e2e-insufficient-quota": "insufficient_quota",
      "e2e-rate-limit": "rate_limit_error",
    };
    if (scenario && errors[scenario]) {
      return NextResponse.json({ success: false, message: "E2E接続確認エラー", error_type: errors[scenario] });
    }
    if (scenario === "e2e-server-error") {
      return NextResponse.json({ detail: "E2E server error" }, { status: 503 });
    }
    if (scenario === "e2e-connection-error") {
      // Break the response stream so the server action follows its fetch/parse catch path.
      return new Response(
        new ReadableStream({
          pull(controller) {
            controller.error(new Error("E2E connection interrupted"));
          },
        }),
      );
    }
  }
  return NextResponse.json({ success: true, message: "E2E用の接続確認結果", error_type: null });
}
