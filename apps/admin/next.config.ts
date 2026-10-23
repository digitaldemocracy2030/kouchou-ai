import path from "node:path";
import type { NextConfig } from "next";
import { buildCspHeaderValue } from "../shared/csp";
import { PROXY_CLIENT_MAX_BODY_SIZE, SERVER_ACTION_BODY_SIZE_LIMIT } from "./app/utils/requestBodyLimit";

const enableGoogleAnalytics = Boolean(process.env.NEXT_PUBLIC_ADMIN_GA_MEASUREMENT_ID);
const contentSecurityPolicy = buildCspHeaderValue({
  apiBasePath: process.env.API_BASEPATH,
  publicApiBasePath: process.env.NEXT_PUBLIC_API_BASEPATH,
  siteUrl: process.env.NEXT_PUBLIC_SITE_URL,
  enableGoogleAnalytics,
  isDevelopment: process.env.NODE_ENV !== "production",
});

const nextConfig: NextConfig = {
  output: "standalone",
  outputFileTracingRoot: path.join(__dirname, "../../"),
  experimental: {
    optimizePackageImports: ["@chakra-ui/react"],
    serverActions: {
      bodySizeLimit: SERVER_ACTION_BODY_SIZE_LIMIT,
    },
    // middleware.ts は全パスで走り、Next はそのために本文を複製する。この上限（既定 10MB）が
    // bodySizeLimit より小さいと、本文が途中で切れて JSON の解析エラー（500）になり、10MB を超える
    // CSV からレポートを作れない。bodySizeLimit より少し大きくする（理由は requestBodyLimit.ts）。
    // 旧名の middlewareClientMaxBodySize と同時に指定すると Next が設定読み込みで例外を投げるので、こちらだけを使う。
    proxyClientMaxBodySize: PROXY_CLIENT_MAX_BODY_SIZE,
  },
  serverExternalPackages: ["fs", "path"],
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          {
            key: "Content-Security-Policy",
            value: contentSecurityPolicy,
          },
        ],
      },
    ];
  },
};

export default nextConfig;
