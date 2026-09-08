import { NextResponse } from "next/server";

export function GET() {
  return NextResponse.json({ success: true, message: "E2E用の接続確認結果", error_type: null });
}
