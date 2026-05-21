import path from "node:path";
import type { NextConfig } from "next";
import { buildCspHeaderValue } from "../shared/csp";

const isStaticExport = process.env.NEXT_PUBLIC_OUTPUT_MODE === "export";
const BASE_PATH = process.env.NEXT_PUBLIC_STATIC_EXPORT_BASE_PATH || "";
const DIST_DIR = process.env.STATIC_EXPORT_DIST_DIR || ".next";
const enableGoogleAnalytics = Boolean(process.env.NEXT_PUBLIC_GA_MEASUREMENT_ID);
const contentSecurityPolicy = buildCspHeaderValue({
  apiBasePath: process.env.API_BASEPATH,
  publicApiBasePath: process.env.NEXT_PUBLIC_API_BASEPATH,
  siteUrl: process.env.NEXT_PUBLIC_SITE_URL,
  enableGoogleAnalytics,
  isDevelopment: process.env.NODE_ENV !== "production",
});

const nextConfig: NextConfig = {
  basePath: isStaticExport ? BASE_PATH : "",
  assetPrefix: isStaticExport ? BASE_PATH : "",
  output: isStaticExport ? "export" : undefined,
  distDir: isStaticExport ? DIST_DIR : ".next",
  trailingSlash: true,
  turbopack: {
    // Ensure Turbopack resolves the monorepo workspace root correctly.
    root: path.join(__dirname, "../.."),
  },
  experimental: {
    optimizePackageImports: ["@chakra-ui/react"],
  },
  async headers() {
    if (isStaticExport) {
      return [];
    }

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
