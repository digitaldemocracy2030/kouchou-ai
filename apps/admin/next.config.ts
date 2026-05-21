import path from "node:path";
import type { NextConfig } from "next";
import { buildCspHeaderValue } from "../shared/csp";

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
      bodySizeLimit: "100mb",
    },
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
