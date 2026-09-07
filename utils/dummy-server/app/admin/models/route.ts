import { NextResponse } from "next/server";
import catalog from "../../../../../apps/api/src/services/model_catalog.json";

export function GET(request: Request) {
  const provider = new URL(request.url).searchParams.get("provider");
  if (provider === "azure") {
    return NextResponse.json([
      { provider, value: "azure-server", label: "サーバー設定を使用", verified: false, available: true, price: null },
    ]);
  }
  if (provider === "local") {
    return NextResponse.json([
      { provider, value: "llama3", label: "Llama 3", verified: false, available: true, price: null },
    ]);
  }
  return NextResponse.json(catalog.filter((model) => model.provider === provider));
}
