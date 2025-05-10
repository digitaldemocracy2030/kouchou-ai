import type { NextRequest } from "next/server";

export async function GET(req: NextRequest) {
  const netlifyEnabled = !!process.env.NETLIFY_AUTH_TOKEN;
  const vercelEnabled = !!process.env.VERCEL_AUTH_TOKEN;
  
  return new Response(JSON.stringify({
    netlifyEnabled,
    vercelEnabled,
    externalHostingEnabled: netlifyEnabled || vercelEnabled
  }), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}
