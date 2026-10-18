import { type NextRequest, NextResponse } from "next/server";

export function middleware(req: NextRequest) {
  if (req.nextUrl.pathname === "/api/healthcheck") {
    return NextResponse.next();
  }

  if (
    process.env.BASIC_AUTH_USERNAME === undefined ||
    process.env.BASIC_AUTH_PASSWORD === undefined ||
    process.env.BASIC_AUTH_USERNAME === "" ||
    process.env.BASIC_AUTH_PASSWORD === ""
  ) {
    return NextResponse.next();
  }
  const basicAuth = req.headers.get("authorization");
  // スキームが Basic で値があるときだけデコードする（不正なヘッダーは 500 ではなく 401 にする）
  const [scheme, authValue] = basicAuth?.split(" ") ?? [];
  if (scheme?.toLowerCase() === "basic" && authValue) {
    const decoded = Buffer.from(authValue, "base64").toString();
    // RFC 7617 ではパスワードに ':' を含められるので、最初の ':' で分ける
    const separator = decoded.indexOf(":");
    if (separator !== -1) {
      const username = decoded.slice(0, separator);
      const password = decoded.slice(separator + 1);
      if (username === process.env.BASIC_AUTH_USERNAME && password === process.env.BASIC_AUTH_PASSWORD) {
        return NextResponse.next();
      }
    }
  }
  return NextResponse.json(
    { error: "Basic Auth Required" },
    {
      headers: { "WWW-Authenticate": 'Basic realm="Secure Area"' },
      status: 401,
    },
  );
}
